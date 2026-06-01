import { memo, useState } from "react";

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function formatPrice(amount) {
  if (amount == null) return "";

  return inrFormatter.format(amount);
}

function MenuItemCard({ item }) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(item.image_url) && !imageFailed;
  const isUnavailable = item.is_available === false;

  return (
    <article
      className={`bg-white py-4 ${
        isUnavailable ? "opacity-60" : ""
      }`}
    >
      <div className="flex gap-3">
        <div className="min-w-0 flex-1">
          <div
            className={`mb-2 flex h-4 w-4 items-center justify-center rounded-sm border ${
              item.is_veg ? "border-emerald-600" : "border-red-600"
            }`}
            aria-label={item.is_veg ? "Vegetarian" : "Non vegetarian"}
            title={item.is_veg ? "Vegetarian" : "Non vegetarian"}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                item.is_veg ? "bg-emerald-600" : "bg-red-600"
              }`}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-[15px] font-semibold leading-snug text-zinc-950">
              {item.name}
            </h3>
            {item.is_special && (
              <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-normal text-orange-700">
                Special
              </span>
            )}
            {item.is_bestseller && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-normal text-amber-700">
                Bestseller
              </span>
            )}
            {isUnavailable && (
              <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[11px] font-medium text-zinc-600">
                Unavailable
              </span>
            )}
          </div>

          <div className="mt-1 flex items-center gap-2">
            <span className="text-sm font-bold text-zinc-950">
              {formatPrice(item.price)}
            </span>
            {item.mrp_price && Number(item.mrp_price) > Number(item.price) && (
              <span className="text-xs text-zinc-400 line-through">
                {formatPrice(item.mrp_price)}
              </span>
            )}
          </div>

          {item.description && (
            <p className="mt-2 max-w-prose text-sm leading-5 text-zinc-600 line-clamp-2">
              {item.description}
            </p>
          )}
        </div>

        <div className="h-24 w-24 flex-shrink-0 overflow-hidden rounded-lg border border-zinc-100 bg-zinc-50 shadow-sm sm:h-28 sm:w-28">
          {hasImage ? (
            <img
              src={item.image_url}
              alt={item.name}
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={() => setImageFailed(true)}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-7 w-7 text-zinc-300"
                fill="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2zM8.5 11.5l2.5 3 3.5-4.5L20 18H4l4.5-6.5z" />
              </svg>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default memo(MenuItemCard);
