import { useAuthStore } from '../store/useAuthStore';
import { UserCircle, Store as StoreIcon } from 'lucide-react';

const Header = () => {
  const user = useAuthStore((state) => state.user);

  // user 정보가 없을 때를 대비한 안전장치
  const username = user?.username || '관리자';
  const role = user?.role === 'staff' ? '직원' : '매장 관리자';
  // 실제 store 정보는 로그인 API 응답에 따라 달라질 수 있으므로 user 객체 구조에 맞게 조정 필요
  const storeName = user?.store_name || '본사'; 

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-40 ml-64">
      <div className="flex items-center text-gray-800">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <StoreIcon className="w-5 h-5 text-gray-500" />
          {storeName}
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900">{username} 님</p>
          <p className="text-xs text-gray-500">{role}</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
          <UserCircle className="w-6 h-6 text-gray-400" />
        </div>
      </div>
    </header>
  );
};

export default Header;