import { memo } from "react";
import MenuItemCard from "./MenuItemCard";

function CategorySection({ category }) {
  const items = category.items || [];

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-zinc-100 bg-white px-4 py-4">
        {category.icon_emoji && (
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-100 text-lg" aria-hidden="true">
            {category.icon_emoji}
          </span>
        )}
        <h2 className="text-base font-bold text-zinc-950">{category.name}</h2>
        <span className="ml-auto rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-600">
          {items.length} {items.length === 1 ? "item" : "items"}
        </span>
      </div>

      {items.length > 0 ? (
        <div className="divide-y divide-zinc-100 px-4">
          {items.map((item) => (
            <MenuItemCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div className="py-8 text-center">
          <p className="text-sm font-medium text-zinc-700">No items in this category</p>
          <p className="mt-1 text-xs text-zinc-500">Add menu items to make this section visible to customers.</p>
        </div>
      )}
    </div>
  );
}

export default memo(CategorySection);
