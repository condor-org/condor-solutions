import { Box } from "@chakra-ui/react";
import Navbar from "./Navbar";
import { useBodyBg } from "../theme/tokens"; // nuevo hook

const MainLayout = ({ children }) => {
  const bg = useBodyBg();

  return (
    <>
      <Navbar />
      <Box as="main" px={4} py={6} bg={bg}>
        {children}
      </Box>
    </>
  );
};

export default MainLayout;
