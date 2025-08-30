// src/components/layout/PageWrapper.jsx
import React from "react";
import { Flex } from "@chakra-ui/react";

const PageWrapper = ({ children }) => {
  return (
    <Flex
      minH="100vh"
      overflow="hidden"
      direction={{ base: "column", md: "row" }} // 👈 columna en mobile, fila en md+
      w="100%"
    >
      {children}
    </Flex>
  );
};

export default PageWrapper;
