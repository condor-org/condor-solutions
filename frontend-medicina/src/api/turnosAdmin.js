// src/api/turnosAdmin.js
import { axiosAuth } from "../utils/axiosAuth";
import { toast } from "react-toastify";
import { AuthContext } from "../auth/AuthContext";
import { useContext, useMemo } from "react";

export function useTurnosAdminApi() {
  const { accessToken, logout } = useContext(AuthContext);
  const api = useMemo(() => axiosAuth(accessToken, logout), [accessToken, logout]);

  const habilitarSuelto = async (turnoId) => {
    try {
      await api.patch(`turnos/${turnoId}/habilitar_suelto/`, {});
      toast.success("Turno habilitado como suelto");
      return true;
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Error al habilitar";
      toast.error(msg);
      return false;
    }
  };

  return { api, habilitarSuelto };
}