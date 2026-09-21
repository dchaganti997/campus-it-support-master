/* =========================================================
   CAMPUS IT SUPPORT
   Microsoft / SharePoint Frontend
========================================================= */


/* =========================================================
   ELEMENTS
========================================================= */

const locationSelect =
  document.getElementById('location');

const locationMessage =
  document.getElementById('locationMessage');

const ticketForm =
  document.getElementById('ticketForm');

const reporterNameInput =
  document.getElementById('reporterName');

const problemDescriptionInput =
  document.getElementById('problemDescription');

const attachmentInput =
  document.getElementById('attachment');

const fileInfo =
  document.getElementById('fileInfo');

const message =
  document.getElementById('message');

const submitButton =
  document.getElementById('submitButton');

const submitButtonText =
  document.getElementById('submitButtonText');


/* =========================================================
   SETTINGS
========================================================= */

const LOCATIONS_API =
  '/api/locations';

const TICKETS_API =
  '/api/tickets';

const LOCATION_CACHE_KEY =
  'campusITLocationsV1';

const MAX_FILE_SIZE =
  8 * 1024 * 1024;


/* Supported by our Teams card setup */

const ALLOWED_FILE_TYPES = [
  'image/jpeg',
  'image/png',
  'video/mp4'
];


/* =========================================================
   LOCATION CACHE
========================================================= */

function getCachedLocations() {

  try {

    const raw =
      localStorage.getItem(
        LOCATION_CACHE_KEY
      );

    if (!raw) {
      return [];
    }

    const locations =
      JSON.parse(raw);

    if (!Array.isArray(locations)) {
      return [];
    }

    return locations;

  } catch (error) {

    console.warn(
      'Unable to read location cache:',
      error
    );

    return [];

  }

}


function saveLocationsToCache(
  locations
) {

  try {

    localStorage.setItem(
      LOCATION_CACHE_KEY,
      JSON.stringify(locations)
    );

  } catch (error) {

    console.warn(
      'Unable to save location cache:',
      error
    );

  }

}


/* =========================================================
   QR LOCATION
========================================================= */

function getRequestedLocationId() {

  const params =
    new URLSearchParams(
      window.location.search
    );

  return (
    params.get('location') || ''
  ).trim();

}


/* =========================================================
   RENDER LOCATIONS
========================================================= */

function renderLocations(
  locations,
  preferredLocationId = ''
) {

  const currentValue =
    locationSelect.value;

  locationSelect.innerHTML =
    '<option value="">Select location</option>';


  locations.forEach(
    function(location) {

      const option =
        document.createElement('option');

      option.value =
        location.id;

      option.textContent =
        location.name;

      locationSelect.appendChild(
        option
      );

    }
  );


  locationSelect.disabled =
    false;


  const locationToSelect =
    preferredLocationId ||
    currentValue;


  if (locationToSelect) {

    const exists =
      locations.some(
        function(location) {

          return (
            location.id ===
            locationToSelect
          );

        }
      );


    if (exists) {

      locationSelect.value =
        locationToSelect;

      updateLocationMessage();

      return;

    }

  }


  locationMessage.textContent =
    'Select the location where the issue is occurring.';

}


/* =========================================================
   LOAD LOCATIONS
========================================================= */

async function loadLocations() {

  const requestedLocationId =
    getRequestedLocationId();


  /*
    Show cached locations immediately.

    This gives us the same fast QR experience
    we had in the previous frontend.
  */

  const cachedLocations =
    getCachedLocations();


  if (cachedLocations.length > 0) {

    renderLocations(
      cachedLocations,
      requestedLocationId
    );

  } else {

    locationSelect.disabled =
      true;

    locationSelect.innerHTML =
      '<option value="">Loading locations...</option>';

    if (requestedLocationId) {

      locationMessage.textContent =
        'Loading selected location...';

    } else {

      locationMessage.textContent =
        'Loading Bearcat Dining locations...';

    }

  }


  /*
    Refresh from SharePoint / Power Automate
    in the background.
  */

  try {

    const response =
      await fetch(
        LOCATIONS_API,
        {
          method: 'GET',
          cache: 'no-store'
        }
      );


    if (!response.ok) {

      throw new Error(
        'Unable to load locations.'
      );

    }


    const data =
      await response.json();


    if (
      !data.success ||
      !Array.isArray(data.locations)
    ) {

      throw new Error(
        data.error ||
        'Invalid location response.'
      );

    }


    saveLocationsToCache(
      data.locations
    );


    renderLocations(
      data.locations,
      requestedLocationId
    );


    /*
      QR exists but is inactive / removed.
    */

    if (requestedLocationId) {

      const qrExists =
        data.locations.some(
          function(location) {

            return (
              location.id ===
              requestedLocationId
            );

          }
        );


      if (!qrExists) {

        locationSelect.value = '';

        locationMessage.textContent =
          'This QR location is currently unavailable. Please select another location.';

      }

    }


  } catch (error) {

    console.error(
      'Location loading error:',
      error
    );


    /*
      If cache exists, don't break the form.
    */

    if (cachedLocations.length > 0) {

      return;

    }


    locationSelect.disabled =
      true;

    locationSelect.innerHTML =
      '<option value="">Unable to load locations</option>';

    locationMessage.textContent =
      'Unable to load locations. Please refresh the page.';

  }

}


/* =========================================================
   LOCATION MESSAGE
========================================================= */

function updateLocationMessage() {

  if (!locationSelect.value) {

    locationMessage.textContent =
      'Select the location where the issue is occurring.';

    return;

  }


  const selectedOption =
    locationSelect.options[
      locationSelect.selectedIndex
    ];


  locationMessage.textContent =
    'Location selected: ' +
    selectedOption.textContent;

}


locationSelect.addEventListener(
  'change',
  updateLocationMessage
);


/* =========================================================
   ATTACHMENT
========================================================= */

attachmentInput.addEventListener(
  'change',
  function() {

    const file =
      attachmentInput.files[0];


    if (!file) {

      fileInfo.textContent = '';

      return;

    }


    const sizeMB =
      file.size /
      (1024 * 1024);


    if (
      !ALLOWED_FILE_TYPES.includes(
        file.type
      )
    ) {

      attachmentInput.value = '';

      fileInfo.textContent =
        'Unsupported file. Use JPG, PNG or MP4.';

      return;

    }


    if (
      file.size >
      MAX_FILE_SIZE
    ) {

      attachmentInput.value = '';

      fileInfo.textContent =
        'File is too large. Maximum size is 8 MB.';

      return;

    }


    const typeLabel =
      file.type.startsWith('video/')
        ? 'MP4 video'
        : 'Photo';


    fileInfo.textContent =
      typeLabel +
      ': ' +
      file.name +
      ' (' +
      sizeMB.toFixed(2) +
      ' MB)';

  }
);


/* =========================================================
   SUBMIT
========================================================= */

ticketForm.addEventListener(
  'submit',
  async function(event) {

    event.preventDefault();


    hideMessage();


    const locationId =
      locationSelect.value.trim();

    const locationName =
      getSelectedLocationName();

    const reporterName =
      reporterNameInput.value.trim();

    const problemDescription =
      problemDescriptionInput.value.trim();


    if (!locationId) {

      showError(
        'Please select a location.'
      );

      return;

    }


    if (!reporterName) {

      showError(
        'Please enter your name.'
      );

      reporterNameInput.focus();

      return;

    }


    if (!problemDescription) {

      showError(
        'Please describe the problem.'
      );

      problemDescriptionInput.focus();

      return;

    }


    const file =
      attachmentInput.files[0];


    /*
      IMPORTANT FOR CURRENT MICROSOFT TEST:

      Our Power Automate flow currently always runs
      "Create file".

      For this first frontend test, choose an
      attachment.

      Once frontend submission is confirmed, we will
      add the no-attachment condition in Power
      Automate and remove this temporary requirement.
    */

    if (!file) {

      showError(
        'For the current Microsoft integration test, please add a JPG, PNG or MP4 attachment.'
      );

      return;

    }


    if (
      !ALLOWED_FILE_TYPES.includes(
        file.type
      )
    ) {

      showError(
        'Please use a JPG, PNG or MP4 file.'
      );

      return;

    }


    if (
      file.size >
      MAX_FILE_SIZE
    ) {

      showError(
        'The attachment must be smaller than 8 MB.'
      );

      return;

    }


    try {

      setSubmittingState(
        true,
        'PREPARING ATTACHMENT...'
      );


      const attachmentData =
        await fileToDataURL(file);


      const payload = {

        locationId:
          locationId,

        locationName:
          locationName,

        reporterName:
          reporterName,

        problemDescription:
          problemDescription,

        attachmentName:
          file.name,

        attachmentType:
          file.type,

        attachmentData:
          attachmentData

      };


      showLoading(
        'Submitting your IT issue...'
      );


      setSubmittingState(
        true,
        'SUBMITTING...'
      );


      const response =
        await fetch(
          TICKETS_API,
          {
            method: 'POST',

            headers: {
              'Content-Type':
                'application/json'
            },

            body:
              JSON.stringify(payload)
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.error ||
          'Unable to submit the ticket.'
        );

      }


      if (!data.success) {

        throw new Error(
          data.error ||
          'Ticket submission failed.'
        );

      }


      showSuccess(
        data.ticketId,
        data.location ||
        locationName
      );


      /*
        Reset reporter/problem/attachment.

        Keep location selected because QR users
        generally remain at the same station.
      */

      reporterNameInput.value = '';

      problemDescriptionInput.value = '';

      attachmentInput.value = '';

      fileInfo.textContent = '';


    } catch (error) {

      console.error(
        'Ticket submission error:',
        error
      );


      showError(
        error.message ||
        'Unable to submit the issue. Please try again.'
      );


    } finally {

      setSubmittingState(
        false
      );

    }

  }
);


/* =========================================================
   FILE → DATA URL
========================================================= */

function fileToDataURL(file) {

  return new Promise(
    function(resolve, reject) {

      const reader =
        new FileReader();


      reader.onload =
        function() {

          resolve(
            reader.result
          );

        };


      reader.onerror =
        function() {

          reject(
            new Error(
              'Unable to read the selected attachment.'
            )
          );

        };


      reader.readAsDataURL(
        file
      );

    }
  );

}


/* =========================================================
   SELECTED LOCATION NAME
========================================================= */

function getSelectedLocationName() {

  if (!locationSelect.value) {
    return '';
  }


  const selectedOption =
    locationSelect.options[
      locationSelect.selectedIndex
    ];


  return (
    selectedOption.textContent || ''
  ).trim();

}


/* =========================================================
   BUTTON STATE
========================================================= */

function setSubmittingState(
  submitting,
  text = 'SUBMIT IT ISSUE'
) {

  submitButton.disabled =
    submitting;

  submitButtonText.textContent =
    text;

}


/* =========================================================
   MESSAGES
========================================================= */

function hideMessage() {

  message.className =
    'message';

  message.style.display =
    'none';

  message.textContent = '';

}


function showLoading(text) {

  message.className =
    'message loading';

  message.style.display =
    'block';

  message.textContent =
    text;

}


function showError(text) {

  message.className =
    'message error';

  message.style.display =
    'block';

  message.textContent =
    text;

}


function showSuccess(
  ticketId,
  locationName
) {

  message.className =
    'message success';

  message.style.display =
    'block';


  message.innerHTML =
    '<strong>Issue submitted successfully.</strong>' +
    '<br>' +
    'Ticket ID: <strong>' +
    escapeHtml(ticketId) +
    '</strong>' +
    '<br>' +
    'Location: ' +
    escapeHtml(locationName) +
    '<br><br>' +
    'Campus IT Support has received your request.';

}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

  const div =
    document.createElement('div');

  div.textContent =
    String(value || '');

  return div.innerHTML;

}


/* =========================================================
   START
========================================================= */

loadLocations();