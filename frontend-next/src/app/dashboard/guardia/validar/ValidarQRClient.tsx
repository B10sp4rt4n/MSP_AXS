"use client";
import GuardiaClient from "../GuardiaClient";

// The legacy QR route uses the same identify-review-confirm flow as caseta.
export default function ValidarQRClient() {
  return <GuardiaClient initialMode="entrada" />;
}
