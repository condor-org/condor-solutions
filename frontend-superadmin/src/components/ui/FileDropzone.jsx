// src/components/ui/FileDropzone.jsx

import React from 'react';
import {
  Box, Input, Text, Button, useColorModeValue, VStack, Icon, VisuallyHidden
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';

const FileDropzone = ({
  id = 'file-dropzone',
  label = 'Subí un archivo',
  accept = 'image/*,application/pdf',
  value,
  onChange,
  onRemove,
  colorScheme = 'green',
}) => {
  const dropzoneBg = useColorModeValue('gray.100', '#232b34');
  const dropzoneHover = useColorModeValue('gray.200', '#243039');
  const dropzoneBorder = useColorModeValue(`${colorScheme}.500`, `${colorScheme}.400`);
  const mutedText = useColorModeValue('gray.600', 'gray.400');

  return (
    <VStack spacing={{ base: 2, md: 3 }} align="stretch" w="100%" minW={0}>
      <Box
        as="label"
        htmlFor={id}
        border="2px dashed"
        borderColor={dropzoneBorder}
        bg={dropzoneBg}
        // ✅ padding responsivo para touch en mobile
        py={{ base: 5, md: 6 }}
        px={{ base: 3, md: 4 }}
        rounded="lg"
        textAlign="center"
        cursor="pointer"
        _hover={{ borderColor: `${colorScheme}.400`, bg: dropzoneHover }}
        // Evita desbordes de texto/líneas largas
        wordBreak="break-word"
      >
        <Input
          id={id}
          type="file"
          accept={accept}
          display="none"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              onChange?.(e.target.files[0]);
            }
          }}
        />
        <Text color={mutedText} fontSize={{ base: 'xs', md: 'sm' }}>
          {value ? `Archivo: ${value.name}` : label}
        </Text>
        <VisuallyHidden>{label}</VisuallyHidden>
      </Box>

      {value && onRemove && (
        <Button
          size={{ base: 'sm', md: 'sm' }}
          colorScheme="red"
          variant="ghost"
          leftIcon={<Icon as={DeleteIcon} />}
          onClick={onRemove}
          alignSelf="start"
          // Evita que el botón de “Quitar” deforme layouts apretados
          flexShrink={0}
        >
          Quitar archivo
        </Button>
      )}
    </VStack>
  );
};

export default FileDropzone;
