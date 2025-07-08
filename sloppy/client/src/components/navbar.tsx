// src/components/navbar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, DollarSign, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Studio", href: "/", icon: Home },
  { name: "Cost Management", href: "/cost-management", icon: DollarSign },
  { name: "Creator Analytics", href: "/creator-analytics", icon: BarChart3 },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="w-64 bg-[#f5f5f5] border-r border-[#e0e0e0] flex flex-col h-full">
      {/* Main Navigation */}
      <div className="px-3 py-4 flex-1">
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  isActive
                    ? "bg-[#f1f1f1] text-[#1a1a1a] font-medium"
                    : "text-[#6b7280] hover:bg-[#e8e8e8] hover:text-[#1a1a1a]"
                )}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
