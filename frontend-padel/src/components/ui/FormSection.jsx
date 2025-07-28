// src/components/ui/FormSection.jsx
import React from 'react';
import { Box, Heading, Text, VStack } from '@chakra-ui/react';
import { useCardColors } from '../theme/tokens';


const FormSection = ({ title, description, children, icon }) => {
  const { bg, color: textColor } = useCardColors();
 // tokens reutilizados para fondo y color dinámico

  return (
    <Box
      bg={bg}
      color={textColor}
      p={[4, 6, 6]}
      rounded="md"
      boxShadow="md"
    >
      <VStack align="start" spacing={4}>
        <Heading size="md" display="flex" alignItems="center" gap={2}>
          {icon && <Box fontSize="lg">{icon}</Box>}
          {title}
        </Heading>
        {description && (
          <Text fontSize="sm" opacity={0.85}>
            {description}
          </Text>
        )}
        <Box w="100%">
          {children}
        </Box>
      </VStack>
    </Box>
  );
};

export default FormSection;
