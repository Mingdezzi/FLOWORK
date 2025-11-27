import { NavLink } from 'react-router-dom';
import { LayoutDashboard, ShoppingCart, Package, Settings, LogOut } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import clsx from 'clsx';

const Sidebar = () => {
  const logout = useAuthStore((state) => state.logout);

  const menuItems = [
    { icon: LayoutDashboard, label: '대시보드', path: '/' },
    { icon: ShoppingCart, label: '판매 등록 (POS)', path: '/pos' },
    { icon: Package, label: '상품/재고 관리', path: '/products' },
    // 추후 추가될 메뉴들
    // { icon: Users, label: '고객 관리', path: '/customers' },
    // { icon: Settings, label: '설정', path: '/settings' },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 h-screen flex flex-col fixed left-0 top-0 z-50">
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <span className="text-xl font-bold text-primary">FLOWORK</span>
      </div>

      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )
            }
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-3 w-full text-left text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          로그아웃
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;