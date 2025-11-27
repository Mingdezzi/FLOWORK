import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import { 
  Megaphone, 
  ShoppingCart, 
  Calendar, 
  ChevronRight, 
  AlertCircle 
} from 'lucide-react';
import { useAuthStore } from '../../store/useAuthStore';

const DashboardPage = () => {
  const user = useAuthStore((state) => state.user);
  
  // React Query를 사용한 데이터 페칭
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const response = await api.get('/dashboard/stats');
      return response.data;
    },
    // 대시보드 데이터는 자주 변할 수 있으므로 1분마다 갱신 (선택사항)
    refetchInterval: 60000, 
  });

  if (isLoading) return <div className="p-8 text-center text-gray-500">데이터를 불러오는 중...</div>;
  if (isError) return <div className="p-8 text-center text-red-500">데이터 로딩에 실패했습니다.</div>;

  const { announcements, pending_orders, weekly_schedules, is_store } = data.data;

  return (
    <div className="space-y-6">
      {/* 1. 공지사항 섹션 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
          <h3 className="font-bold text-gray-800 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-red-500" />
            공지사항
          </h3>
          <button className="text-sm text-gray-500 hover:text-gray-700 flex items-center">
            더보기 <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <ul className="divide-y divide-gray-100">
          {announcements?.length > 0 ? (
            announcements.map((item) => (
              <li key={item.id} className="px-6 py-3 hover:bg-gray-50 transition-colors cursor-pointer">
                <div className="flex justify-between items-center">
                  <span className="text-gray-700 font-medium truncate flex-1 pr-4">{item.title}</span>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{item.date}</span>
                </div>
                <p className="text-sm text-gray-500 mt-1 truncate">{item.content_preview}</p>
              </li>
            ))
          ) : (
            <li className="px-6 py-8 text-center text-gray-400 text-sm">등록된 공지사항이 없습니다.</li>
          )}
        </ul>
      </div>

      {/* 매장 계정 전용 섹션 */}
      {is_store && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* 2. 진행 중인 주문 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800 flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-blue-500" />
                진행 중인 주문
              </h3>
              <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                {pending_orders?.length || 0}건
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                  <tr>
                    <th className="px-6 py-3">고객명</th>
                    <th className="px-6 py-3">상품명</th>
                    <th className="px-6 py-3 text-center">상태</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {pending_orders?.length > 0 ? (
                    pending_orders.map((order) => (
                      <tr key={order.id} className="hover:bg-gray-50 cursor-pointer">
                        <td className="px-6 py-3 font-medium text-gray-900">{order.customer_name}</td>
                        <td className="px-6 py-3 text-gray-500 truncate max-w-[150px]">{order.product_name}</td>
                        <td className="px-6 py-3 text-center">
                          <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs">
                            {order.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="px-6 py-8 text-center text-gray-400">진행 중인 주문이 없습니다.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. 주간 일정 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <h3 className="font-bold text-gray-800 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-green-500" />
                이번 주 일정
              </h3>
            </div>
            <ul className="divide-y divide-gray-100">
              {weekly_schedules?.length > 0 ? (
                weekly_schedules.map((schedule, idx) => (
                  <li key={idx} className="px-6 py-3 hover:bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span 
                        className="w-2 h-2 rounded-full" 
                        style={{ backgroundColor: schedule.color || '#ccc' }}
                      ></span>
                      <div>
                        <p className="text-sm font-medium text-gray-800">
                          {schedule.title} 
                          <span className="text-gray-400 font-normal ml-1">({schedule.staff_name})</span>
                        </p>
                        <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded mt-1 inline-block">
                          {schedule.type}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs font-semibold text-gray-500">{schedule.date_str}</span>
                  </li>
                ))
              ) : (
                <li className="px-6 py-8 text-center text-gray-400 text-sm">예정된 일정이 없습니다.</li>
              )}
            </ul>
          </div>

        </div>
      )}
    </div>
  );
};

export default DashboardPage;