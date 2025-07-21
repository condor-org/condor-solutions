import React, { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user } = useContext(AuthContext);

  if (!user) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(user.tipo_usuario)) {
    return <Navigate to="/login" />;
  }

  return children;
};

export default ProtectedRoute;
