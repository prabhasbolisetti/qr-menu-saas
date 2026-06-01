import { memo } from "react";
import MenuItemCard from "./MenuItemCard";

function CategorySection({ category }) {
  const items = category.items || [];

  return (
    <div className="rounded-lg border border-gray-100 bg-white px-4 shadow-sm">
      <div className="flex items-center gap-2 border-b border-gray-100 py-4">
        {category.icon_emoji && (
          <span className="text-xl" aria-hidden="true">
            {category.icon_emoji}
          </span>
        )}
        <h2 className="text-base font-bold text-gray-950">{category.name}</h2>
        <span className="ml-auto text-xs font-medium text-gray-500">
          {items.length} {items.length === 1 ? "item" : "items"}
        </span>
      </div>

      {items.length > 0 ? (
        <div>
          {items.map((item) => (
            <MenuItemCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div className="py-8 text-center">
          <p className="text-sm font-medium text-gray-700">No items in this category</p>
          <p className="mt-1 text-xs text-gray-500">Add menu items to make this section visible to customers.</p>
        </div>
      )}
    </div>
  );
}

export default memo(CategorySection);
