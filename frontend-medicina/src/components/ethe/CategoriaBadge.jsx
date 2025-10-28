import React from 'react';
import { Badge } from '@chakra-ui/react';

const CategoriaBadge = ({ categoria, size = "md" }) => {
  const getColorScheme = (categoria) => {
    switch (categoria) {
      case 'C1': return 'green';
      case 'C2': return 'orange';
      case 'C3': return 'red';
      default: return 'gray';
    }
  };
  
  const getLabel = (categoria) => {
    switch (categoria) {
      case 'C1': return 'C1 - Estable';
      case 'C2': return 'C2 - Moderado';
      case 'C3': return 'C3 - Avanzado';
      default: return categoria;
    }
  };
  
  return (
    <Badge 
      colorScheme={getColorScheme(categoria)} 
      size={size}
      fontWeight="bold"
    >
      {getLabel(categoria)}
    </Badge>
  );
};

export default CategoriaBadge;