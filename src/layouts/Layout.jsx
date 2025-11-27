import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />
      <Header />
      
      {/* Header 높이(h-16 = 4rem)와 Sidebar 너비(w-64 = 16rem)를 고려한 
        콘텐츠 영역 마진 및 패딩 설정 
      */}
      <main className="ml-64 p-6">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;