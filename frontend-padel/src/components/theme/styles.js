// src/components/theme/styles.js

const styles = {
  global: (props) => ({
    "html, body, #root": {
      height: "100%",
      bg: props.colorMode === 'dark' ? 'gray.900' : 'gray.100',
      color: props.colorMode === 'dark' ? 'white' : 'gray.800',
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      margin: 0,
      padding: 0,
      lineHeight: "1.6",
    },
    a: {
      color: "blue.400",
      _hover: { color: "blue.500" },
    },
    "input, textarea, select": {
      bg: props.colorMode === 'dark' ? 'gray.800' : 'white',
      color: props.colorMode === 'dark' ? 'white' : 'gray.800',
      borderColor: "gray.600",
      _focus: {
        borderColor: "blue.400",
        boxShadow: "0 0 0 1px #4299e1",
      },
    },
    button: {
      fontWeight: "600",
      borderRadius: "md",
      _focus: {
        boxShadow: "0 0 0 3px rgba(66,153,225,0.6)",
      },
    },
    "::-webkit-scrollbar": {
      width: "10px",
    },
    "::-webkit-scrollbar-track": {
      background: props.colorMode === 'dark' ? "#1A202C" : "#EDF2F7",
    },
    "::-webkit-scrollbar-thumb": {
      background: "#4299E1",
      borderRadius: "10px",
    },
  }),
};

export default styles;
