# MC Press Design System

**Story**: STORY-004.5
**Status**: Substantially Complete
**Last Updated**: October 6, 2025

## Overview

This design system provides standardized components and design tokens based on MC Press's official brand colors. All components follow WCAG AA accessibility standards and use consistent spacing, typography, and color scales.

## Official MC Press Brand Colors

All components use these official brand colors defined in `design-tokens.css`:

| Color | Hex Code | Usage |
|-------|----------|-------|
| **Blue** | `#878DBC` | Primary actions, navigation, links |
| **Green** | `#A1A88B` | Success states, confirmations |
| **Orange** | `#EF9537` | CTAs, "Buy Now" buttons, high-priority actions |
| **Red** | `#990000` | Errors, warnings, destructive actions |
| **Gray** | `#A3A2A2` | Secondary text, borders, disabled states |

## Available Components

### ✅ Implemented Components

All components are located in `/frontend/components/design-system/`:

1. **Button** (`Button/`)
   - Variants: primary, secondary, tertiary, danger, success, cta
   - Sizes: sm, md, lg
   - States: default, hover, active, disabled, loading
   - Features: icons, full-width, loading spinner

2. **Alert** (`Alert/`)
   - Variants: success, error, warning, info
   - Features: closable, with title, custom icons

3. **Input** (`Input/`)
   - Types: text, number, email, password, textarea
   - States: default, focus, error, disabled
   - Features: labels, error messages, helper text

4. **Card** (`Card/`)
   - Features: header, body, footer sections
   - Variants: default, elevated (with shadow)

5. **Modal** (`Modal/`)
   - Features: overlay, close button, focus trap
   - Sizes: sm, md, lg, full

6. **Loading** (`Loading/`)
   - Components: Spinner, Skeleton, ProgressBar
   - Multiple sizes and colors

7. **Badge** (`Badge/`)
   - Variants: default, success, warning, danger, info
   - Sizes: sm, md, lg

### Component Import

```typescript
// Import from barrel export
import { Button, Alert, Input, Card, Modal, Badge } from '@/components/design-system'
import { Spinner, Skeleton, ProgressBar } from '@/components/design-system/Loading'

// Usage
<Button variant="primary" size="md">Click Me</Button>
<Alert variant="success">Operation completed!</Alert>
```

## Design Tokens

All design tokens are CSS custom properties defined in `/frontend/app/styles/design-tokens.css`:

### Colors
```css
--mc-blue: #878DBC;
--mc-green: #A1A88B;
--mc-orange: #EF9537;
--mc-red: #990000;
--mc-gray: #A3A2A2;
```

### Semantic Colors
```css
--color-primary: var(--mc-blue);
--color-success: var(--mc-green);
--color-warning: var(--mc-orange);
--color-danger: var(--mc-red);
--color-cta: var(--mc-orange);
```

### Typography
```css
--font-size-xs: 0.75rem;    /* 12px */
--font-size-sm: 0.875rem;   /* 14px */
--font-size-base: 1rem;     /* 16px */
--font-size-lg: 1.125rem;   /* 18px */
--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
```

### Spacing
```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
```

### Border Radius
```css
--radius-sm: 0.25rem;   /* 4px */
--radius-md: 0.375rem;  /* 6px */
--radius-lg: 0.5rem;    /* 8px */
--radius-xl: 0.75rem;   /* 12px */
--radius-full: 9999px;
```

### Shadows
```css
--shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
```

## Usage Examples

### Button Component

```typescript
// Primary button (MC Blue)
<Button variant="primary" size="md">
  Primary Action
</Button>

// CTA button (MC Orange - for revenue-critical actions)
<Button variant="cta" size="lg">
  Buy Now
</Button>

// Success button (MC Green)
<Button variant="success" size="md">
  Confirm
</Button>

// Danger button (MC Red)
<Button variant="danger" size="sm">
  Delete
</Button>

// With loading state
<Button variant="primary" loading={true}>
  Processing...
</Button>
```

### Alert Component

```typescript
// Success alert
<Alert variant="success" title="Success!">
  Your changes have been saved.
</Alert>

// Error alert
<Alert variant="error" title="Error" closable onClose={() => {}}>
  Something went wrong. Please try again.
</Alert>

// Warning alert
<Alert variant="warning">
  This action cannot be undone.
</Alert>
```

### Using Design Tokens in Custom Components

```typescript
// In a component's style attribute
<div style={{
  backgroundColor: 'var(--mc-blue)',
  padding: 'var(--space-4)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-md)'
}}>
  Custom styled element
</div>

// In CSS modules
.myComponent {
  color: var(--text-primary);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  padding: var(--space-4) var(--space-6);
  border-radius: var(--radius-md);
}
```

## Accessibility

All components follow WCAG AA standards:
- ✅ Color contrast ratios meet 4.5:1 minimum
- ✅ Focus states visible with `--border-focus`
- ✅ Keyboard navigation support
- ✅ Screen reader compatible (ARIA labels)
- ✅ Respects `prefers-reduced-motion`
- ✅ High contrast mode support

## File Structure

```
frontend/
├── app/
│   └── styles/
│       └── design-tokens.css          # All CSS custom properties
└── components/
    └── design-system/
        ├── index.ts                   # Barrel export
        ├── Button/
        │   ├── Button.tsx
        │   ├── Button.module.css
        │   └── Button.test.tsx
        ├── Alert/
        │   ├── Alert.tsx
        │   ├── Alert.module.css
        │   └── Alert.test.tsx
        ├── Input/
        ├── Card/
        ├── Modal/
        ├── Loading/
        │   ├── Spinner.tsx
        │   ├── Skeleton.tsx
        │   ├── ProgressBar.tsx
        │   └── Loading.module.css
        ├── Badge/
        └── README.md                  # This file
```

## Future Enhancements

The following components were planned but deferred to future stories:

- **Select/Dropdown** - For form dropdowns
- **Table** - For data tables
- **Tabs** - For tabbed interfaces
- **Tooltip** - For contextual help
- **Storybook** - Interactive component documentation

These will be implemented as needed by future feature stories.

## Implementation Status

✅ **Complete:**
- All 5 MC Press brand colors implemented
- 7 core components built and tested
- Design tokens system established
- Typography, spacing, shadows defined
- Accessibility standards met
- Applied to homepage

❌ **Deferred:**
- Storybook documentation
- 4 additional components (Select, Table, Tabs, Tooltip)

## Contributing

When adding new components:

1. Use MC Press brand colors via CSS custom properties
2. Follow existing component structure (component + module.css + test)
3. Ensure WCAG AA accessibility compliance
4. Add to barrel export in `index.ts`
5. Document usage in this README

## Questions or Issues?

Refer to Story 004.5 documentation for full requirements and acceptance criteria.
