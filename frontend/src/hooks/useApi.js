import { useCallback, useEffect, useState } from "react";
import { api, errMsg } from "@/lib/api";

export function useApi(path, params) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify(params || {});

  const load = useCallback(() => {
    if (!path) return;
    setLoading(true);
    api
      .get(path, { params: JSON.parse(key) })
      .then((r) => { setData(r.data); setError(null); })
      .catch((e) => setError(errMsg(e)))
      .finally(() => setLoading(false));
  }, [path, key]);

  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load };
}
