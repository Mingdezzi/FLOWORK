import { create } from 'zustand';

export const useCartStore = create((set, get) => ({
  cart: [],

  // 상품 추가 (이미 있으면 수량 증가)
  addToCart: (product) => {
    const { cart } = get();
    const existingItem = cart.find((item) => item.id === product.id);

    if (existingItem) {
      set({
        cart: cart.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        ),
      });
    } else {
      set({ cart: [...cart, { ...product, quantity: 1 }] });
    }
  },

  // 수량 변경
  updateQuantity: (productId, quantity) => {
    const { cart } = get();
    if (quantity <= 0) {
      set({ cart: cart.filter((item) => item.id !== productId) });
    } else {
      set({
        cart: cart.map((item) =>
          item.id === productId ? { ...item, quantity } : item
        ),
      });
    }
  },

  // 상품 삭제
  removeFromCart: (productId) => {
    set({ cart: get().cart.filter((item) => item.id !== productId) });
  },

  // 장바구니 비우기
  clearCart: () => set({ cart: [] }),

  // 총액 계산 (Getter)
  getTotalAmount: () => {
    return get().cart.reduce((total, item) => total + item.price * item.quantity, 0);
  },
}));