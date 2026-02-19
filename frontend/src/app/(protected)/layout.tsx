import { onAuthenticateUser } from "@/actions/user";
import React from "react";

type Props = {
  children: React.ReactNode;
};

export const dynamic = 'force-dynamic';

/**
 * Protected layout for JurisScope.
 * No authentication redirect - hardcoded user is always "authenticated".
 */
const layout = async (props: Props) => {
  // Initialize the hardcoded user (creates in DB if needed)
  await onAuthenticateUser();
  
  return <div className="w-full min-h-screen">{props.children}</div>;
};

export default layout;
