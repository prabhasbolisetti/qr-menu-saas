import { useState } from "react";
import { downloadImage } from "../utils/download";

function copyTextFallback(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();
  document.execCommand("copy");
  textArea.remove();
}

export default function QRCodePanel({
  qr,
  restaurantSlug,
  title = "Restaurant QR code",
  description = "Permanent scan link for guests.",
  onNotice,
}) {
  const [copied, setCopied] = useState(false);

  if (!qr) return null;

  const fileName = `${restaurantSlug || qr.slug || "restaurant"}-qr.png`;

  async function copyMenuLink() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(qr.menu_url);
      } else {
        copyTextFallback(qr.menu_url);
      }

      setCopied(true);
      onNotice?.("Menu link copied");
      setTimeout(() => setCopied(false), 1800);
    } catch {
      onNotice?.("Copy failed. Select and copy the link manually.");
    }
  }

  return (
    <section className="rounded-lg border border-gray-100 bg-white p-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="flex flex-shrink-0 items-center justify-center rounded-lg border border-gray-100 bg-white p-2 shadow-sm">
          <img
            src={qr.qr_image_url}
            alt="Restaurant QR code"
            className="h-32 w-32 rounded object-contain"
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-bold text-gray-950">{title}</h2>
            <span className="rounded-full bg-green-50 px-2.5 py-1 text-xs font-semibold text-green-700">
              Customer-ready
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">{description}</p>
          <p className="mt-3 break-all rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700">
            {qr.menu_url}
          </p>
        </div>

        <div className="grid gap-2 sm:grid-cols-3 md:w-40 md:grid-cols-1">
          <button
            type="button"
            onClick={copyMenuLink}
            className="h-10 rounded-lg border border-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50"
          >
            {copied ? "Copied" : "Copy link"}
          </button>
          <a
            href={qr.menu_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50"
          >
            Open menu
          </a>
          <button
            type="button"
            onClick={() => downloadImage(qr.qr_image_url, fileName)}
            className="h-10 rounded-lg bg-gray-950 px-4 text-sm font-semibold text-white hover:bg-gray-800"
          >
            Download QR
          </button>
        </div>
      </div>
    </section>
  );
}
