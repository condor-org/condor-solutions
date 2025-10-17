// src/components/ui/InfoCard.jsx

import React from 'react';
import { Flex, VStack, Text, IconButton, useColorModeValue } from '@chakra-ui/react';
import { CopyIcon } from '@chakra-ui/icons';
import { useCardColors, useMutedText } from '../theme/tokens';
import { toast } from 'react-toastify';

const InfoCard = ({ label, value, copyButton = false, ...props }) => {
  const card = useCardColors();
  const mutedText = useMutedText();
  const hoverBg = useColorModeValue("gray.50", "gray.600");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success("Copiado al portapapeles");
    } catch (error) {
      console.error("Error copiando al portapapeles:", error);
      toast.error("Error al copiar");
    }
  };

  return (
    <Flex
      align="center"
      justify="space-between"
      p={4}
      bg={card.bg}
      color={card.color}
      borderRadius="md"
      borderWidth="1px"
      borderColor="gray.200"
      _hover={copyButton ? { bg: hoverBg } : {}}
      transition="background-color 0.2s ease"
      {...props}
    >
      <VStack align="start" spacing={1} flex="1" minW={0}>
        <Text fontSize="sm" color={mutedText} fontWeight="medium">
          {label}
        </Text>
        <Text 
          fontWeight="medium" 
          noOfLines={2}
          wordBreak="break-word"
        >
          {value || "No informado"}
        </Text>
      </VStack>
      {copyButton && (
        <IconButton
          icon={<CopyIcon />}
          size="sm"
          variant="ghost"
          colorScheme="blue"
          onClick={handleCopy}
          ml={3}
          flexShrink={0}
          aria-label="Copiar"
        />
      )}
    </Flex>
  );
};

export default InfoCard;
