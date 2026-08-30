import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex min-h-11 w-fit shrink-0 items-center justify-center gap-2 rounded-sm border px-4 text-sm font-extrabold tracking-[-0.01em] outline-none transition-[transform,background-color,border-color,color,opacity] duration-150 ease-[cubic-bezier(.23,1,.32,1)] select-none active:scale-[.97] focus-visible:ring-3 focus-visible:ring-[#2e64f5]/30 disabled:pointer-events-none disabled:opacity-45',
  {
    variants: {
      variant: {
        default: 'border-[#17201c] bg-[#17201c] text-[#f7f4ea] hover:bg-[#27342e]',
        signal: 'border-[#ff5c35] bg-[#ff5c35] text-[#17201c] hover:bg-[#ff7656]',
        outline: 'border-[#918b7e] bg-transparent text-[#17201c] hover:border-[#17201c] hover:bg-white/45',
        quiet: 'border-transparent bg-[#e8e3d7] text-[#17201c] hover:bg-[#ddd6c7]',
        danger: 'border-[#c83a20] bg-transparent text-[#a92f1b] hover:bg-[#c83a20] hover:text-white',
      },
      size: { default: 'h-11', sm: 'min-h-9 px-3 text-xs', lg: 'min-h-12 px-5 text-base', icon: 'size-11 p-0' },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export function Button({ className, variant, size, asChild = false, ...props }:
  React.ComponentProps<'button'> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : 'button'
  return <Component type={asChild ? undefined : 'button'} className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
