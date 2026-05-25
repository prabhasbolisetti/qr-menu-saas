import {
  BrowserRouter,
  Routes,
  Route,
  Navigate
} from "react-router-dom";

import PublicMenu from "../pages/PublicMenu";
import OwnerDashboard from "../pages/OwnerDashboard";
import SuperDashboard from "../pages/SuperDashboard";
import RestaurantDetails from "../pages/RestaurantDetails";
import Login from "../pages/Login";

import ProtectedRoute from "../components/ProtectedRoute";

export default function AppRoutes() {

  return (

    <BrowserRouter>

      <Routes>

        <Route
          path="/"
          element={<Navigate to="/login" />}
        />

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/menu/:slug"
          element={<PublicMenu />}
        />

        <Route
          path="/owner"
          element={
            <ProtectedRoute allowedRoles={["owner"]}>
              <OwnerDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/super"
          element={
            <ProtectedRoute allowedRoles={["super"]}>
              <SuperDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/super/restaurants/:id"
          element={
            <ProtectedRoute allowedRoles={["super"]}>
              <RestaurantDetails />
            </ProtectedRoute>
          }
        />

      </Routes>

    </BrowserRouter>
  );
}