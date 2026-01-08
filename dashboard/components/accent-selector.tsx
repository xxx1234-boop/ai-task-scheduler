"use client"

import * as React from "react"
import { Check, Palette } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

const ACCENT_COLORS = [
  { name: "default", label: "Default", color: "bg-zinc-500" },
  { name: "blue", label: "Blue", color: "bg-blue-500" },
  { name: "green", label: "Green", color: "bg-green-500" },
  { name: "red", label: "Red", color: "bg-red-500" },
  { name: "orange", label: "Orange", color: "bg-orange-500" },
  { name: "yellow", label: "Yellow", color: "bg-yellow-500" },
  { name: "violet", label: "Violet", color: "bg-violet-500" },
  { name: "rose", label: "Rose", color: "bg-rose-500" },
] as const

type AccentColor = (typeof ACCENT_COLORS)[number]["name"]

export function AccentSelector() {
  const [accent, setAccent] = React.useState<AccentColor>("default")
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
    const savedAccent = localStorage.getItem("accent-color") as AccentColor | null
    if (savedAccent) {
      setAccent(savedAccent)
      applyAccent(savedAccent)
    }
  }, [])

  const applyAccent = (color: AccentColor) => {
    const root = document.documentElement
    if (color === "default") {
      root.removeAttribute("data-accent")
    } else {
      root.setAttribute("data-accent", color)
    }
  }

  const handleAccentChange = (color: AccentColor) => {
    setAccent(color)
    applyAccent(color)
    localStorage.setItem("accent-color", color)
  }

  if (!mounted) {
    return (
      <Button variant="outline" size="icon" disabled>
        <Palette className="h-[1.2rem] w-[1.2rem]" />
      </Button>
    )
  }

  const currentColor = ACCENT_COLORS.find((c) => c.name === accent)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <div
            className={cn(
              "h-4 w-4 rounded-full",
              currentColor?.color || "bg-zinc-500"
            )}
          />
          <span className="sr-only">Select accent color</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Accent Color</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {ACCENT_COLORS.map((color) => (
          <DropdownMenuItem
            key={color.name}
            onClick={() => handleAccentChange(color.name)}
            className="flex items-center gap-2"
          >
            <div className={cn("h-4 w-4 rounded-full", color.color)} />
            <span>{color.label}</span>
            {accent === color.name && <Check className="ml-auto h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
