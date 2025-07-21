// src/components/ui/FileDropzone.jsx

import React from 'react';
import {
  Box, Input, Text, Button, useColorModeValue, VStack, Icon
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
    <VStack spacing={3} align="stretch">
      <Box
        as="label"
        htmlFor={id}
        border="2px dashed"
        borderColor={dropzoneBorder}
        bg={dropzoneBg}
        py={6}
        px={4}
        rounded="lg"
        textAlign="center"
        cursor="pointer"
        _hover={{ borderColor: `${colorScheme}.400`, bg: dropzoneHover }}
      >
        <Input
          id={id}
          type="file"
          accept={accept}
          display="none"
          onChange={(e) => {
            if (e.target.files[0]) {
              onChange?.(e.target.files[0]);
            }
          }}
        />
        <Text color={mutedText}>
          {value ? `Archivo: ${value.name}` : label}
        </Text>
      </Box>

      {value && onRemove && (
        <Button
          size="sm"
          colorScheme="red"
          variant="ghost"
          leftIcon={<Icon as={DeleteIcon} />}
          onClick={onRemove}
          alignSelf="start"
        >
          Quitar archivo
        </Button>
      )}
    </VStack>
  );
};

export default FileDropzone;
