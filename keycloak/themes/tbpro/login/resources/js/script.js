window.addEventListener('load', (evt) => {
  const zoneinfo = document.getElementById('zoneinfo');
  if (zoneinfo) {
    zoneinfo.value = Intl.DateTimeFormat().resolvedOptions().timeZone ?? 'UTC';
    zoneinfo.setAttribute('readonly', 'readonly');
  }
});