import { StateBlock } from "../ui";

/* Kerangka state panel dashboard — tinggi tetap 176px (parity Stitch)
   supaya tata letak tidak bergeser antara loading / kosong / galat.
   Dipakai juga oleh halaman Evaluasi Model. */
export const PanelState = ({
  kind,
  message,
}: {
  kind: "loading" | "error";
  message?: string;
}) => (
  <div className="p-3">
    <StateBlock state={kind} height={176} hint={message} />
  </div>
);
