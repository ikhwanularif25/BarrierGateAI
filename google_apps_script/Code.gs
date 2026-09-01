const CONFIG = {
  SPREADSHEET_ID: 'PASTE_SPREADSHEET_ID_HERE',
  SHEET_NAME: 'FUNCTIONAL_TEST',
  DRIVE_FOLDER_ID: 'PASTE_DRIVE_FOLDER_ID_HERE'
};

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents || '{}');
    validatePayload_(payload);

    const imageUrl = saveImage_(payload);
    appendRow_(payload, imageUrl);

    return jsonResponse_({
      ok: true,
      event_id: payload.event_id,
      image_url: imageUrl
    });
  } catch (err) {
    return jsonResponse_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

function validatePayload_(p) {
  const required = [
    'event_id',
    'timestamp',
    'camera',
    'zone',
    'detection',
    'confidence',
    'image_base64'
  ];

  required.forEach(function (key) {
    if (p[key] === undefined || p[key] === null || p[key] === '') {
      throw new Error('Missing field: ' + key);
    }
  });
}

function saveImage_(p) {
  const folder = DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID);
  const bytes = Utilities.base64Decode(p.image_base64);
  const filename = p.snapshot_file || (p.event_id + '.jpg');
  const blob = Utilities.newBlob(bytes, p.image_mime_type || 'image/jpeg', filename);
  const file = folder.createFile(blob);

  // Link dapat dibuka oleh user yang memang punya akses ke file/folder Drive.
  return file.getUrl();
}

function appendRow_(p, imageUrl) {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      'Timestamp',
      'Event ID',
      'Camera',
      'Zone',
      'Detection',
      'Load Status',
      'Confidence',
      'Source',
      'Snapshot File',
      'Image URL'
    ]);
    sheet.getRange(1, 1, 1, 10).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }

  sheet.appendRow([
    p.timestamp,
    p.event_id,
    p.camera,
    p.zone,
    p.detection,
    p.load_status || '',
    Number(p.confidence),
    p.source || '',
    p.snapshot_file || '',
    imageUrl
  ]);
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function testSetup() {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const folder = DriveApp.getFolderById(CONFIG.DRIVE_FOLDER_ID);
  Logger.log('Spreadsheet: ' + ss.getName());
  Logger.log('Folder: ' + folder.getName());
}
