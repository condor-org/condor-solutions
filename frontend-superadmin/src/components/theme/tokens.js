import { useColorMode } from '@chakra-ui/react';

const visualSets = {
  classic: {
    modal: { light: 'white', dark: 'gray.800' },
    modalText: { light: 'gray.800', dark: 'whiteAlpha.900' },

    inputBg: { light: 'white', dark: 'gray.700' },
    inputText: { light: 'gray.800', dark: 'white' },
    inputBorder: { light: 'gray.300', dark: 'gray.600' },

    muted: { light: 'gray.600', dark: 'gray.400' },

    cardBg: { light: 'white', dark: 'gray.700' },
    cardText: { light: 'gray.800', dark: 'whiteAlpha.900' },
    cardIcon: { light: 'blue.600', dark: 'blue.300' },

    navbarBg: { light: 'gray.700', dark: 'gray.800' },
    navbarText: { light: 'whiteAlpha.900', dark: 'whiteAlpha.900' },
    navbarBorder: { light: 'brand.500', dark: 'gray.700' },
    navbarHover: { light: 'brand.300', dark: 'whiteAlpha.800' },

    body: { light: 'gray.200', dark: 'gray.800' },
  },

  alt: {
    modal:         { light: 'orange.50',      dark: 'purple.900' },
    modalText:     { light: 'orange.700',     dark: 'purple.100' },
  
    inputBg:       { light: 'orange.100',     dark: 'purple.700' },
    inputText:     { light: 'orange.900',     dark: 'white' },
    inputBorder:   { light: 'orange.300',     dark: 'purple.500' },
  
    muted:         { light: 'orange.600',     dark: 'purple.300' },
  
    cardBg:        { light: 'orange.50',      dark: 'purple.800' },
    cardText:      { light: 'orange.800',     dark: 'whiteAlpha.900' },
    cardIcon:      { light: 'pink.500',       dark: 'cyan.300' },
  
    navbarBg:      { light: 'pink.500',       dark: 'cyan.900' },
    navbarText:    { light: 'whiteAlpha.900', dark: 'whiteAlpha.900' },
    navbarBorder:  { light: 'orange.400',     dark: 'cyan.700' },
    navbarHover:   { light: 'orange.300',     dark: 'cyan.500' },
  
    body:          { light: 'orange.100',     dark: 'gray.950' },
  }
};

// 🔄 Elegí el set activo para testeos visuales
const ACTIVE_SET = visualSets.classic;

export const useModalColors = () => {
  const { colorMode } = useColorMode();
  return {
    bg: ACTIVE_SET.modal[colorMode],
    color: ACTIVE_SET.modalText[colorMode],
  };
};

export const useInputColors = () => {
  const { colorMode } = useColorMode();
  return {
    bg: ACTIVE_SET.inputBg[colorMode],
    color: ACTIVE_SET.inputText[colorMode],
    borderColor: ACTIVE_SET.inputBorder[colorMode],
  };
};

export const useMutedText = () => {
  const { colorMode } = useColorMode();
  return ACTIVE_SET.muted[colorMode];
};

export const useCardColors = () => {
  const { colorMode } = useColorMode();
  return {
    bg: ACTIVE_SET.cardBg[colorMode],
    color: ACTIVE_SET.cardText[colorMode],
    iconColor: ACTIVE_SET.cardIcon[colorMode],
  };
};

export const useNavbarTokens = () => {
  const { colorMode } = useColorMode();
  return {
    bg: ACTIVE_SET.navbarBg[colorMode],
    borderColor: ACTIVE_SET.navbarBorder[colorMode],
    color: ACTIVE_SET.navbarText[colorMode],
    iconColor: ACTIVE_SET.navbarText[colorMode],
    hoverColor: ACTIVE_SET.navbarHover[colorMode],
    textColor: ACTIVE_SET.navbarText[colorMode],
    emailOpacity: 0.85,
    mode: colorMode,
  };
};

export const useBodyBg = () => {
  const { colorMode } = useColorMode();
  return ACTIVE_SET.body[colorMode];
};
