"""
Shared Selenium utilities for Swaya.me test scripts.
Import into any Selenium script for JS error collection and fetch interception.
"""

JS_ERROR_COLLECTOR = """
window.__jsErrors = [];
window.addEventListener('error', function(e) {
  window.__jsErrors.push({msg: e.message, src: e.filename, line: e.lineno, col: e.colno});
});
window.addEventListener('unhandledrejection', function(e) {
  window.__jsErrors.push({msg: 'UnhandledPromise: ' + (e.reason?.message || String(e.reason)), src: '', line: 0});
});
"""

JS_FETCH_INTERCEPTOR = """
(function() {
  if (window.__fetchIntercepted) return;
  window.__fetchIntercepted = true;
  window.__failedFetches = [];
  const _fetch = window.fetch;
  window.fetch = function(...args) {
    return _fetch(...args).then(function(res) {
      if (res.status >= 400) {
        window.__failedFetches.push({url: args[0], status: res.status});
      }
      return res;
    });
  };
})();
"""


def inject_error_collectors(driver):
    """Inject JS error and failed-fetch collectors into the current page."""
    driver.execute_script(JS_ERROR_COLLECTOR)
    driver.execute_script(JS_FETCH_INTERCEPTOR)


def collect_js_errors(driver, phase_name=""):
    """Return collected JS errors; print a warning if any were found."""
    errors = driver.execute_script('return window.__jsErrors || []')
    failed = driver.execute_script('return window.__failedFetches || []')
    if errors:
        prefix = f"[{phase_name}] " if phase_name else ""
        print(f"WARN {prefix}TC-STB-002 JS errors: {errors[:3]}")
    if failed:
        prefix = f"[{phase_name}] " if phase_name else ""
        print(f"WARN {prefix}TC-STB-002 Failed API calls: {failed[:3]}")
    return errors, failed
