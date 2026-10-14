import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const ClientLogo = ({ clientId, version, className, testid }) => {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let obj = null;
    let alive = true;
    setUrl(null);
    if (!clientId) return undefined;
    api.get(`/clients/${clientId}/logo`, { responseType: "blob" })
      .then((r) => { if (alive) { obj = URL.createObjectURL(r.data); setUrl(obj); } })
      .catch(() => {});
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj); };
  }, [clientId, version]);
  if (!url) return null;
  return <img src={url} alt="Client logo" className={className} data-testid={testid} />;
};
