"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";

type Provider = "whatsapp" | "facebook" | "instagram";
type Identity = { provider: Provider; reference: string | null; verified_at: string | null; revoked_at: string | null };
type Profile = { usuario_id: string; celular: string | null; celular_verified_at: string | null; identities: Identity[] };
const PROVIDERS: Provider[] = ["whatsapp", "facebook", "instagram"];
const LABELS = { whatsapp: "WhatsApp", facebook: "Facebook", instagram: "Instagram" };

export default function IdentityProfile() {
  const { getToken } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    getToken().then(token => {
      if (!token) throw new Error("Sin sesión");
      return api.get<Profile>("/auth/me/identity", token, controller.signal);
    }).then(data => { if (!controller.signal.aborted) { setProfile(data); setError(""); } })
      .catch(() => { if (!controller.signal.aborted) setError("No se pudo cargar tu perfil."); });
    return () => controller.abort();
  }, [getToken, attempt]);

  async function save(field: "celular" | Provider, value: string | null, consent: boolean) {
    setBusy(true); setError(""); setMessage("");
    try {
      const token = await getToken();
      if (!token) throw new Error("Sin sesión");
      const data = field === "celular"
        ? await api.patch<Profile>("/auth/me/identity", { celular: value, consent }, token)
        : value === null
          ? await api.delete<Profile>(`/auth/me/identity/external/${field}`, token)
          : await api.put<Profile>(`/auth/me/identity/external/${field}`, { reference: value, consent }, token);
      setProfile(data); setMessage(value === null ? "Dato retirado y autorización revocada." : "Guardado en tu perfil.");
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudo guardar."); }
    finally { setBusy(false); }
  }

  return <section className="mt-8 rounded-xl border border-gray-700 bg-gray-900 p-5" aria-labelledby="identity-title">
    <h2 id="identity-title" className="text-xl font-semibold">Mi identidad AXS</h2>
    <p className="my-3 text-sm text-gray-300">Completa estos datos cuando quieras. Son privados y opcionales; no cambian tus permisos ni tu acceso. No activan mensajes ni conexiones con redes sociales.</p>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {message && <p role="status" className="text-green-300">{message}</p>}
    {!profile && !error && <p role="status">Cargando perfil…</p>}
    {!profile && error && <button onClick={() => setAttempt(n => n + 1)}>Reintentar</button>}
    {profile && <>
      <p className="text-sm text-gray-400 break-all">Identificador AXS: {profile.usuario_id}</p>
      <IdentityField key={`celular:${profile.celular}`} name="celular" label="Celular" value={profile.celular}
        verified={!!profile.celular_verified_at} busy={busy} save={save} />
      {PROVIDERS.map(provider => {
        const identity = profile.identities.find(row => row.provider === provider && !row.revoked_at);
        return <IdentityField key={`${provider}:${identity?.reference}`} name={provider} label={LABELS[provider]}
          value={identity?.reference ?? null} verified={!!identity?.verified_at} busy={busy} save={save} />;
      })}
    </>}
  </section>;
}

function IdentityField({ name, label, value, verified, busy, save }: {
  name: "celular" | Provider; label: string; value: string | null; verified: boolean; busy: boolean;
  save: (field: "celular" | Provider, value: string | null, consent: boolean) => Promise<void>;
}) {
  const [draft, setDraft] = useState(value ?? "");
  const [consent, setConsent] = useState(false);
  const phone = name === "celular" || name === "whatsapp";
  return <form className="mt-5 border-t border-gray-700 pt-4" onSubmit={event => {
    event.preventDefault(); void save(name, draft.trim(), consent).then(() => setConsent(false));
  }}>
    <fieldset disabled={busy}>
      <label htmlFor={`identity-${name}`} className="block font-medium">{label} (opcional)</label>
      <input id={`identity-${name}`} className="mt-2 w-full rounded border border-gray-600 bg-gray-950 p-2"
        type={phone ? "tel" : "url"} maxLength={phone ? 16 : 300} value={draft}
        placeholder={phone ? "+525512345678" : `https://${name}.com/usuario`}
        aria-describedby={`identity-${name}-status`} onChange={event => setDraft(event.target.value)} />
      <p id={`identity-${name}-status`} className="mt-1 text-sm text-gray-400">
        {value ? (verified ? "Verificado" : "Declarado por ti; sin verificar") : "Sin registrar"}
        {name === "whatsapp" && ". Puede ser distinto de tu celular."}
      </p>
      <label className="mt-2 flex items-start gap-2 text-sm text-gray-300">
        <input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />
        Autorizo guardar este dato en mi perfil privado. Puedo retirarlo cuando quiera.
      </label>
      <div className="mt-3 flex gap-4">
        <button type="submit" disabled={!draft.trim() || !consent} className="rounded bg-blue-700 px-3 py-2 disabled:opacity-40">Guardar {label}</button>
        {value && <button type="button" onClick={() => void save(name, null, false)} className="text-red-300">Retirar {label}</button>}
      </div>
    </fieldset>
  </form>;
}
