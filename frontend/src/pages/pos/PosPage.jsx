import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../lib/api';
import { useDebounce } from '../../hooks/useDebounce';
import { useCartStore } from '../../store/useCartStore';
import { 
  Search, 
  ShoppingCart, 
  Trash2, 
  Plus, 
  Minus, 
  CreditCard, 
  RefreshCcw,
  Receipt
} from 'lucide-react';

const PosPage = () => {
  // 상태 관리
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 300);
  const [activeTab, setActiveTab] = useState('pos'); // 'pos' | 'history'

  // 장바구니 스토어 (Zustand)
  const { cart, addToCart, updateQuantity, removeFromCart, clearCart, getTotalAmount } = useCartStore();
  const totalAmount = getTotalAmount();

  const queryClient = useQueryClient();

  // 1. 상품 검색 쿼리
  const { data: productsData, isLoading: isSearchLoading } = useQuery({
    queryKey: ['products', debouncedSearch],
    queryFn: async () => {
      // 검색어가 없으면 빈 배열 반환 (또는 추천 상품)
      if (!debouncedSearch) return { items: [] };
      const response = await api.get('/products', {
        params: { q: debouncedSearch, limit: 20 }
      });
      return response.data;
    },
    enabled: !!debouncedSearch, // 검색어가 있을 때만 실행
  });

  // 2. 판매 등록 뮤테이션
  const saleMutation = useMutation({
    mutationFn: async (saleData) => {
      return await api.post('/sales', saleData);
    },
    onSuccess: () => {
      alert('판매가 완료되었습니다.');
      clearCart();
      queryClient.invalidateQueries(['salesHistory']); // 판매 이력 갱신
    },
    onError: (error) => {
      alert(error.response?.data?.message || '판매 등록 실패');
    }
  });

  const handleCheckout = () => {
    if (cart.length === 0) return alert('장바구니가 비어있습니다.');
    if (!confirm(`총 ${totalAmount.toLocaleString()}원을 결제하시겠습니까?`)) return;

    const saleData = {
      items: cart.map(item => ({
        variant_id: item.variants?.[0]?.id || item.id, // 단순화를 위해 첫 번째 옵션 사용 가정
        quantity: item.quantity,
        price: item.price
      })),
      payment_method: 'CARD' // 추후 UI에서 선택 가능하도록 확장
    };

    saleMutation.mutate(saleData);
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col md:flex-row gap-4">
      
      {/* --- 좌측 패널: 상품 검색 및 목록 --- */}
      <div className="w-full md:w-2/3 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {/* 탭 헤더 */}
        <div className="flex border-b border-gray-200">
          <button 
            className={`flex-1 py-4 text-center font-medium ${activeTab === 'pos' ? 'text-primary border-b-2 border-primary bg-primary/5' : 'text-gray-500 hover:bg-gray-50'}`}
            onClick={() => setActiveTab('pos')}
          >
            판매 등록
          </button>
          <button 
            className={`flex-1 py-4 text-center font-medium ${activeTab === 'history' ? 'text-primary border-b-2 border-primary bg-primary/5' : 'text-gray-500 hover:bg-gray-50'}`}
            onClick={() => setActiveTab('history')}
          >
            판매 이력
          </button>
        </div>

        {activeTab === 'pos' ? (
          <>
            {/* 검색바 */}
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                  placeholder="상품명 또는 바코드를 스캔/입력하세요..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
              </div>
            </div>

            {/* 상품 목록 */}
            <div className="flex-1 overflow-y-auto p-4">
              {isSearchLoading ? (
                <div className="text-center py-10 text-gray-500">검색 중...</div>
              ) : productsData?.items?.length > 0 ? (
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                  {productsData.items.map((product) => (
                    <div 
                      key={product.id} 
                      className="border border-gray-200 rounded-lg p-3 hover:border-primary hover:shadow-md cursor-pointer transition-all flex flex-col justify-between h-32"
                      onClick={() => addToCart(product)}
                    >
                      <div>
                        <h4 className="font-bold text-gray-800 line-clamp-1">{product.name}</h4>
                        <p className="text-xs text-gray-500">{product.code}</p>
                      </div>
                      <div className="flex justify-between items-end mt-2">
                        <span className="text-lg font-bold text-primary">{product.price.toLocaleString()}원</span>
                        <span className={`text-xs px-2 py-1 rounded-full ${product.total_stock > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          재고: {product.total_stock}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <ShoppingCart className="w-12 h-12 mb-2 opacity-20" />
                  <p>상품을 검색하거나 바코드를 스캔하세요.</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <SalesHistoryTab />
        )}
      </div>

      {/* --- 우측 패널: 장바구니 (항상 표시) --- */}
      <div className="w-full md:w-1/3 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-900 text-white flex justify-between items-center">
          <h2 className="font-bold flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" /> 장바구니
          </h2>
          <button 
            onClick={clearCart}
            className="text-xs text-gray-300 hover:text-white flex items-center gap-1"
          >
            <RefreshCcw className="w-3 h-3" /> 초기화
          </button>
        </div>

        {/* 장바구니 아이템 목록 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
          {cart.length > 0 ? (
            cart.map((item) => (
              <div key={item.id} className="bg-white p-3 rounded-lg shadow-sm border border-gray-200 flex flex-col gap-2">
                <div className="flex justify-between items-start">
                  <span className="font-medium text-gray-800 line-clamp-1">{item.name}</span>
                  <button onClick={() => removeFromCart(item.id)} className="text-gray-400 hover:text-red-500">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex justify-between items-center">
                  <div className="flex items-center border border-gray-300 rounded-md bg-white">
                    <button 
                      onClick={() => updateQuantity(item.id, item.quantity - 1)}
                      className="p-1 hover:bg-gray-100 text-gray-600"
                    >
                      <Minus className="w-3 h-3" />
                    </button>
                    <span className="w-8 text-center text-sm font-medium">{item.quantity}</span>
                    <button 
                      onClick={() => updateQuantity(item.id, item.quantity + 1)}
                      className="p-1 hover:bg-gray-100 text-gray-600"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>
                  <span className="font-bold text-gray-900">{(item.price * item.quantity).toLocaleString()}원</span>
                </div>
              </div>
            ))
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 opacity-50">
              <Receipt className="w-16 h-16 mb-2" />
              <p className="text-sm">장바구니가 비어있습니다.</p>
            </div>
          )}
        </div>

        {/* 결제 요약 및 버튼 */}
        <div className="p-4 border-t border-gray-200 bg-white space-y-4">
          <div className="flex justify-between items-center text-gray-600">
            <span>총 수량</span>
            <span>{cart.reduce((acc, item) => acc + item.quantity, 0)}개</span>
          </div>
          <div className="flex justify-between items-center text-2xl font-bold text-primary">
            <span>결제 금액</span>
            <span>{totalAmount.toLocaleString()}원</span>
          </div>
          
          <button
            onClick={handleCheckout}
            disabled={cart.length === 0 || saleMutation.isPending}
            className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-4 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-md"
          >
            {saleMutation.isPending ? (
              '처리 중...'
            ) : (
              <>
                <CreditCard className="w-6 h-6" /> 결제하기
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

// --- 하위 컴포넌트: 판매 이력 (간단 버전) ---
const SalesHistoryTab = () => {
  // 실제 API 연동 시 useQuery 사용
  // const { data } = useQuery(...) 
  const dummyHistory = [
    { id: 1, time: '14:30', amount: 45000, type: '카드', items: '나이키 에어포스 외 1건' },
    { id: 2, time: '13:15', amount: 12000, type: '현금', items: '양말 세트' },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-gray-700 uppercase bg-gray-50 sticky top-0">
          <tr>
            <th className="px-6 py-3">시간</th>
            <th className="px-6 py-3">내역</th>
            <th className="px-6 py-3 text-right">금액</th>
            <th className="px-6 py-3 text-center">결제</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {dummyHistory.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50 cursor-pointer">
              <td className="px-6 py-4 text-gray-500">{item.time}</td>
              <td className="px-6 py-4 font-medium text-gray-900">{item.items}</td>
              <td className="px-6 py-4 text-right font-bold">{item.amount.toLocaleString()}</td>
              <td className="px-6 py-4 text-center">
                <span className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">{item.type}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-4 text-center text-xs text-gray-400">
        최근 10건의 내역만 표시됩니다.
      </div>
    </div>
  );
};

export default PosPage;