// src/components/layout/PageWrapper.jsx

import React from 'react';
import { Flex } from '@chakra-ui/react';

const PageWrapper = ({ children }) => {
  return (
    <Flex minH="100vh" overflow="hidden">
      {children}
    </Flex>
  );
};

export default PageWrapper;
