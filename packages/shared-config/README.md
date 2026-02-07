# Shared Configuration

Shared configuration files for Next.js apps in the Fantasy Sports monorepo.

## Contents

### `tailwind.config.js`
Base Tailwind CSS configuration that can be extended by individual apps.

### `tsconfig.base.json`
Base TypeScript configuration with common compiler options.

## Usage

### In Next.js Apps

#### Tailwind Config

```javascript
// apps/your-app/tailwind.config.ts
import baseConfig from '@fantasy/shared-config/tailwind'

export default {
  ...baseConfig,
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      // Your app-specific theme extensions
    },
  },
}
```

#### TypeScript Config

```json
// apps/your-app/tsconfig.json
{
  "extends": "@fantasy/shared-config/tsconfig",
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
```

## Benefits

- ✅ Consistent configuration across all Next.js apps
- ✅ Single source of truth for compiler options
- ✅ Easy to update configuration in one place
- ✅ Reduces configuration boilerplate

## Apps Using This Config

- `apps/baseball-dashboard`
- `apps/fantasy-hub`
