import React from "react";

type Props = {
  children: React.ReactNode;
};

const Layout = (props: Props) => {
  return (
    <div className="pb-20 h-full overflow-x-hidden pt-10 px-6">
      {props.children}
    </div>
  );
};

export default Layout;
