// src/components/ui/FormSection.jsx
import React from 'react';
import { Box, Heading, Text, VStack } from '@chakra-ui/react';
import { useCardColors } from '../theme/tokens';

const FormSection = ({ title, description, children, icon }) => {
  const { bg, color: textColor } = useCardColors();

  return (
    <Box
      bg={bg}
      color={textColor}
      p={{ base: 4, md: 6 }}
      rounded="md"
      boxShadow="md"
      w="100%"
      minW={0}
    >
      <VStack align="start" spacing={{ base: 3, md: 4 }} w="100%" minW={0}>
        <Heading
          size={{ base: 'sm', md: 'md' }}
          display="flex"
          alignItems="center"
          gap={2}
          w="100%"
          minW={0}
        >
          {icon && <Box fontSize={{ base: 'md', md: 'lg' }}>{icon}</Box>}
          <Text as="span" noOfLines={2} wordBreak="break-word">
            {title}
          </Text>
        </Heading>

        {description && (
          <Text fontSize={{ base: 'xs', md: 'sm' }} opacity={0.85} wordBreak="break-word">
            {description}
          </Text>
        )}

        <Box w="100%" minW={0}>
          {children}
        </Box>
      </VStack>
    </Box>
  );
};

export default FormSection;
