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
    '^@/components/ui/progress$': '<rootDir>/__mocks__/@/components/ui/progress.tsx',
    '^@/components/ui/alert$': '<rootDir>/__mocks__/@/components/ui/alert.tsx',
    '^@/components/ui/textarea$': '<rootDir>/__mocks__/@/components/ui/textarea.tsx',
    '^@/components/ui/label$': '<rootDir>/__mocks__/@/components/ui/label.tsx',
    '^@/components/ui/input$': '<rootDir>/__mocks__/@/components/ui/input.tsx',
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
  testPathIgnorePatterns: [
    '<rootDir>/e2e/',
  ],
}
