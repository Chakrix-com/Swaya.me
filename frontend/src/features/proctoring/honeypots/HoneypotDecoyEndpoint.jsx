export function HoneypotDecoyEndpoint({ config }) {
  if (!config?.decoy_endpoint_param) return null;
  return (
    <div
      data-submit-url={`/api/v1/proctoring/honeypot?trap=dom_scrape&t=${config.decoy_endpoint_param}`}
      style={{ display: 'none' }}
    />
  );
}
