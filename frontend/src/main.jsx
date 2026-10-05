import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import {
  AuthProvider,
  Protected,
  PublicLayout,
  WorkspaceLayout,
} from "./components";
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import Converter from "./pages/Converter";
import History from "./pages/History";
import Profile from "./pages/Profile";
import Admin from "./pages/Admin";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <AuthProvider>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Landing />} />
          {["login", "register", "forgot", "reset", "verify", "resend"].map(
            (mode) => (
              <Route
                key={mode}
                path={`/${mode}`}
                element={<Auth key={mode} mode={mode} />}
              />
            ),
          )}
        </Route>
        <Route element={<Protected />}>
          <Route element={<WorkspaceLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/converter" element={<Converter />} />
            <Route path="/history" element={<History />} />
            <Route path="/profile" element={<Profile />} />
            <Route element={<Protected admin />}>
              <Route path="/admin" element={<Admin />} />
            </Route>
          </Route>
        </Route>
        <Route
          path="*"
          element={
            <main className="empty">
              <h1>Page not found</h1>
              <Link to="/">Return home</Link>
            </main>
          }
        />
      </Routes>
    </AuthProvider>
  </BrowserRouter>,
);
