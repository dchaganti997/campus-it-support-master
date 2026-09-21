import json
import os
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))

TICKET_FLOW_URL = os.environ.get("TICKET_FLOW_URL", "").strip()
LOCATIONS_FLOW_URL = os.environ.get("LOCATIONS_FLOW_URL", "").strip()


class CampusITHandler(SimpleHTTPRequestHandler):

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        self.wfile.write(body)


    def call_power_automate(self, url, payload):
        if not url:
            raise RuntimeError(
                "Power Automate URL is not configured."
            )

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                response_body = response.read()

                if not response_body:
                    return {
                        "success": True
                    }

                return json.loads(
                    response_body.decode("utf-8")
                )

        except urllib.error.HTTPError as error:

            error_body = error.read().decode(
                "utf-8",
                errors="replace"
            )

            raise RuntimeError(
                f"Power Automate returned HTTP "
                f"{error.code}: {error_body}"
            )

        except urllib.error.URLError as error:

            raise RuntimeError(
                f"Unable to reach Power Automate: "
                f"{error.reason}"
            )


    def do_GET(self):

        if self.path.startswith("/api/locations"):

            try:

                result = self.call_power_automate(
                    LOCATIONS_FLOW_URL,
                    {}
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

        super().do_GET()


    def do_POST(self):

        if self.path != "/api/tickets":

            self.send_json(
                404,
                {
                    "success": False,
                    "error": "API endpoint not found."
                }
            )

            return

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw_body = self.rfile.read(
                content_length
            )

            payload = json.loads(
                raw_body.decode("utf-8")
            )

            required_fields = [
                "locationId",
                "locationName",
                "reporterName",
                "problemDescription"
            ]

            for field in required_fields:

                if not str(
                    payload.get(field, "")
                ).strip():

                    self.send_json(
                        400,
                        {
                            "success": False,
                            "error":
                                f"Missing required field: "
                                f"{field}"
                        }
                    )

                    return

            result = self.call_power_automate(
                TICKET_FLOW_URL,
                payload
            )

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


if __name__ == "__main__":

    if not TICKET_FLOW_URL:
        print(
            "ERROR: TICKET_FLOW_URL is not set."
        )
        raise SystemExit(1)

    if not LOCATIONS_FLOW_URL:
        print(
            "ERROR: LOCATIONS_FLOW_URL is not set."
        )
        raise SystemExit(1)

    print()
    print("Campus IT frontend server")
    print("-------------------------")
    print(f"http://localhost:{PORT}")
    print()
    print(
        "Power Automate URLs loaded privately "
        "from environment variables."
    )
    print()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        CampusITHandler
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
