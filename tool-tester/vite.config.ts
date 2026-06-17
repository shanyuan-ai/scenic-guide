// tool-tester/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { spawn } from 'child_process'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'start-backend-middleware',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === '/api/system/start-backend' && req.method === 'POST') {
            const projectRoot = path.resolve(__dirname, '..');
            
            // 启动 FastAPI 后端服务
            const child = spawn(
              'python',
              ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
              {
                cwd: projectRoot,
                detached: true,
                stdio: 'ignore',
                shell: true // 在 Windows 上以 shell 方式运行更稳妥，可以自动寻址 python 全局环境变量
              }
            );
            
            child.unref();
            
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'success', message: '后端服务启动命令已发送' }));
          } else {
            next();
          }
        });
      }
    }
  ],
})
