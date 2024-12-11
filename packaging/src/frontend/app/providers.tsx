'use client';

import { CacheProvider } from '@chakra-ui/next-js'
import { ChakraProvider, ChakraProviderProps } from '@chakra-ui/react'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CacheProvider>
      <ChakraProvider resetCSS theme={undefined}>
        {children}
      </ChakraProvider>
    </CacheProvider>
  )
}