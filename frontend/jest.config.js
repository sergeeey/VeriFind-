/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'jest-environment-jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
    '^@/components/ui/card$': '<rootDir>/__mocks__/@/components/ui/card.tsx',
    '^@/components/ui/select$': '<rootDir>/__mocks__/@/components/ui/select.tsx',
    '^@/components/ui/skeleton$': '<rootDir>/__mocks__/@/components/ui/skeleton.tsx',
    '^@/components/ui/table$': '<rootDir>/__mocks__/@/components/ui/table.tsx',
    '^@/components/ui/badge$': '<rootDir>/__mocks__/@/components/ui/badge.tsx',
    '^@/components/ui/button$': '<rootDir>/__mocks__/@/components/ui/button.tsx',
  },
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        tsconfig: {
          jsx: 'react-jsx',
        },
      },
    ],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(lucide-react|@radix-ui)/)',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
}
