import React from 'react';
import { Badge, HStack, Text } from '@chakra-ui/react';
import { FaCheck, FaTimes, FaClock } from 'react-icons/fa';

const AsistenciaBadge = ({ asistio, size = "sm" }) => {
  if (asistio === null) {
    return (
      <HStack spacing={1}>
        <FaClock color="gray" size={12} />
        <Badge colorScheme="gray" size={size}>
          Pendiente
        </Badge>
      </HStack>
    );
  }
  
  if (asistio === true) {
    return (
      <HStack spacing={1}>
        <FaCheck color="green" size={12} />
        <Badge colorScheme="green" size={size}>
          Asistió
        </Badge>
      </HStack>
    );
  }
  
  return (
    <HStack spacing={1}>
      <FaTimes color="red" size={12} />
      <Badge colorScheme="red" size={size}>
        No asistió
      </Badge>
    </HStack>
  );
};

export default AsistenciaBadge;