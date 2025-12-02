import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ChakraProvider, extendTheme, ColorModeScript } from '@chakra-ui/react'
import App from './App'

const theme = extendTheme({
  config: { initialColorMode: 'dark', useSystemColorMode: false },
  styles: {
    global: {
      'html, body, #root': { height: '100%' },
      body: { bg: 'gray.900', color: 'gray.100' },
    },
  },
})

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ChakraProvider>
  </React.StrictMode>
)
