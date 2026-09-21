import json
import os
import urllib.request
import urllib.error

from http.server import (
    ThreadingHTTPServer,
    SimpleHTTPRequestHandler
)


# =========================================================
# SERVER SETTINGS
# =========================================================

HOST = "0.0.0.0"

PORT = int(
    os.environ.get(
        "PORT",
        "8000"
    )
)


# =========================================================
# PRIVATE POWER AUTOMATE URLS
#
# These are NOT stored in GitHub.
#
# Local Mac:
# export TICKET_FLOW_URL='...'
# export LOCATIONS_FLOW_URL='...'
#
# Render:
# Add both as Environment Variables.
# =========================================================

TICKET_FLOW_URL = os.environ.get(
    "TICKET_FLOW_URL",
    ""
).strip()

LOCATIONS_FLOW_URL = os.environ.get(
    "LOCATIONS_FLOW_URL",
    ""
).strip()


# =========================================================
# REQUEST HANDLER
# =========================================================

class CampusITHandler(
    SimpleHTTPRequestHandler
):


    # =====================================================
    # JSON RESPONSE HELPER
    # =====================================================

    def send_json(
        self,
        status_code,
        payload
    ):

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.send_header(
            "X-Content-Type-Options",
            "nosniff"
        )

        self.end_headers()

        self.wfile.write(
            body
        )


    # =====================================================
    # CALL POWER AUTOMATE
    # =====================================================

    def call_power_automate(
        self,
        url,
        payload
    ):

        if not url:

            raise RuntimeError(
                "Power Automate URL is not configured."
            )


        data = json.dumps(
            payload
        ).encode(
            "utf-8"
        )


        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type":
                    "application/json"
            },
            method="POST"
        )


        try:

            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                response_body = (
                    response.read()
                )


                if not response_body:

                    return {
                        "success": True
                    }


                return json.loads(
                    response_body.decode(
                        "utf-8"
                    )
                )


        except urllib.error.HTTPError as error:

            error_body = (
                error.read().decode(
                    "utf-8",
                    errors="replace"
                )
            )

            raise RuntimeError(
                "Power Automate returned HTTP "
                f"{error.code}: "
                f"{error_body}"
            )


        except urllib.error.URLError as error:

            raise RuntimeError(
                "Unable to reach Power Automate: "
                f"{error.reason}"
            )


        except TimeoutError:

            raise RuntimeError(
                "Power Automate request timed out."
            )


    # =====================================================
    # GET REQUESTS
    # =====================================================

    def do_GET(self):


        # -------------------------------------------------
        # HEALTH CHECK
        # Used by Render
        # -------------------------------------------------

        if (
            self.path == "/health" or
            self.path.startswith(
                "/health?"
            )
        ):

            self.send_json(
                200,
                {
                    "status": "ok"
                }
            )

            return


        # -------------------------------------------------
        # LOCATIONS API
        # Browser:
        # GET /api/locations
        #
        # Server:
        # POST {} to Power Automate
        # -------------------------------------------------

        if self.path.startswith(
            "/api/locations"
        ):

            try:

                result = (
                    self.call_power_automate(
                        LOCATIONS_FLOW_URL,
                        {}
                    )
                )

                self.send_json(
                    200,
                    result
                )


            except Exception as error:

                print(
                    "Locations API error:",
                    error
                )

                self.send_json(
                    500,
                    {
                        "success": False,
                        "error": str(error)
                    }
                )


            return


        # -------------------------------------------------
        # ALL OTHER GET REQUESTS
        #
        # index.html
        # style.css
        # app.js
        # assets/*
        # -------------------------------------------------

        super().do_GET()


    # =====================================================
    # POST REQUESTS
    # =====================================================

    def do_POST(self):


        # -------------------------------------------------
        # ONLY ALLOW /api/tickets
        # -------------------------------------------------

        if self.path != "/api/tickets":

            self.send_json(
                404,
                {
                    "success": False,
                    "error":
                        "API endpoint not found."
                }
            )

            return


        try:


            # -------------------------------------------------
            # CONTENT LENGTH
            # -------------------------------------------------

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )


            # 15 MB safety limit for JSON request.
            #
            # Frontend currently limits uploaded file
            # to 8 MB. Base64 increases request size.
            # -------------------------------------------------

            MAX_REQUEST_SIZE = (
                15 * 1024 * 1024
            )


            if (
                content_length >
                MAX_REQUEST_SIZE
            ):

                self.send_json(
                    413,
                    {
                        "success": False,
                        "error":
                            "Request is too large."
                    }
                )

                return


            if content_length <= 0:

                self.send_json(
                    400,
                    {
                        "success": False,
                        "error":
                            "Request body is empty."
                    }
                )

                return


            # -------------------------------------------------
            # READ BODY
            # -------------------------------------------------

            raw_body = self.rfile.read(
                content_length
            )


            payload = json.loads(
                raw_body.decode(
                    "utf-8"
                )
            )


            # -------------------------------------------------
            # REQUIRED FIELDS
            # -------------------------------------------------

            required_fields = [
                "locationId",
                "locationName",
                "reporterName",
                "problemDescription"
            ]


            for field in required_fields:

                value = str(
                    payload.get(
                        field,
                        ""
                    )
                ).strip()


                if not value:

                    self.send_json(
                        400,
                        {
                            "success": False,
                            "error":
                                "Missing required field: "
                                f"{field}"
                        }
                    )

                    return


            # -------------------------------------------------
            # CLEAN BASIC STRING FIELDS
            # -------------------------------------------------

            payload["locationId"] = str(
                payload.get(
                    "locationId",
                    ""
                )
            ).strip()

            payload["locationName"] = str(
                payload.get(
                    "locationName",
                    ""
                )
            ).strip()

            payload["reporterName"] = str(
                payload.get(
                    "reporterName",
                    ""
                )
            ).strip()

            payload["problemDescription"] = str(
                payload.get(
                    "problemDescription",
                    ""
                )
            ).strip()


            # -------------------------------------------------
            # OPTIONAL ATTACHMENT VALUES
            #
            # Power Automate currently still expects
            # an attachment for the first production test.
            #
            # We will modify Power Automate later so these
            # become truly optional.
            # -------------------------------------------------

            payload["attachmentName"] = str(
                payload.get(
                    "attachmentName",
                    ""
                )
            ).strip()

            payload["attachmentType"] = str(
                payload.get(
                    "attachmentType",
                    ""
                )
            ).strip()

            payload["attachmentData"] = str(
                payload.get(
                    "attachmentData",
                    ""
                )
            ).strip()


            # -------------------------------------------------
            # CALL POWER AUTOMATE
            # -------------------------------------------------

            result = (
                self.call_power_automate(
                    TICKET_FLOW_URL,
                    payload
                )
            )


            # -------------------------------------------------
            # RETURN POWER AUTOMATE RESPONSE
            # -------------------------------------------------

            self.send_json(
                200,
                result
            )


        except json.JSONDecodeError:

            self.send_json(
                400,
                {
                    "success": False,
                    "error":
                        "Request body must be valid JSON."
                }
            )


        except UnicodeDecodeError:

            self.send_json(
                400,
                {
                    "success": False,
                    "error":
                        "Invalid request encoding."
                }
            )


        except Exception as error:

            print(
                "Ticket API error:",
                error
            )

            self.send_json(
                500,
                {
                    "success": False,
                    "error": str(error)
                }
            )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":


    # -----------------------------------------------------
    # MAKE SURE BOTH URLs EXIST
    # -----------------------------------------------------

    if not TICKET_FLOW_URL:

        print(
            "ERROR: "
            "TICKET_FLOW_URL is not set."
        )

        raise SystemExit(1)


    if not LOCATIONS_FLOW_URL:

        print(
            "ERROR: "
            "LOCATIONS_FLOW_URL is not set."
        )

        raise SystemExit(1)


    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    print()
    print(
        "Campus IT frontend server"
    )
    print(
        "-------------------------"
    )

    print(
        f"Listening on "
        f"http://{HOST}:{PORT}"
    )

    print()

    print(
        "Power Automate URLs loaded "
        "privately from environment variables."
    )

    print()


    server = ThreadingHTTPServer(
        (
            HOST,
            PORT
        ),
        CampusITHandler
    )


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print(
            "\nServer stopped."
        )

        server.server_close()
