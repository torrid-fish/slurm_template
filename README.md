# Slurm Template Repository

SLURM 作業提交工具集，特別為機器學習工作流設計。

## 安裝

```bash
git clone https://github.com/torrid-fish/slurm_template.git ~/.slurm_template
# 添加到 .bashrc 或 .zshrc
export PATH="~/.slurm_template/bin:$PATH"
```

## 工具

### `ssubmit` - 增強型 SLURM 提交工具

**核心特點：**
- 🔒 **代碼版本隔離**：每次提交時自動創建獨立的代碼快照（git worktree），確保作業執行的代碼版本固定
- 📁 **數據共享**：通過軟連接共享大型目錄（data、checkpoints 等），避免重複複製
- 🎛️ **參數化配置**：輕鬆指定 SLURM 參數，無需編寫 batch script
- 🧹 **自動清理**：提交失敗時自動清理快照和 worktree
- 📋 **統一日誌管理**：自動創建和管理日誌目錄

**基本用法：**

```bash
# 簡單提交
ssubmit 'python train.py'

# 指定 GPU
ssubmit --gres=gpu:h100:1 'python train.py'

# 指定多個 SLURM 參數
ssubmit -N 2 -n 4 --time=2-00:00:00 --gres=gpu:a100:2 'python train.py --batch_size=256'

# 帶虛擬環境
ssubmit 'source .venv/bin/activate && python train.py'

# 複雜命令
ssubmit 'bash -c "source .venv/bin/activate && python train.py --config config.yaml"'
```

**常用 SLURM 選項：**

| 選項 | 說明 | 例子 |
|------|------|------|
| `-N` | 節點數 | `-N 2` |
| `-n` | 任務數 | `-n 4` |
| `-c` | 每任務 CPU 核心數 | `-c 8` |
| `-p` | 分區名稱 | `-p gpu_partition` |
| `--time` | 時間限制 | `--time=2-00:00:00` (2天) |
| `--gres` | 通用資源（GPU等） | `--gres=gpu:h100:2` |

## 必要的目錄結構

`ssubmit` 需要以下目錄結構。如果某個目錄不存在，會被自動跳過：

```
project-root/
├── data/                 # 數據集（會被軟連接共享）
├── checkpoints/          # 模型檢查點（會被軟連接共享）
├── output/              # 輸出結果（會被軟連接共享）
├── wandb/               # Weights & Biases 日誌（會被軟連接共享）
├── .venv/               # Python 虛擬環境（會被軟連接共享）
├── train.py
└── ...
```

## 重要注意事項

### 1. Git 工作樹必須乾淨
```bash
# 提交前必須提交所有更改
git add .
git commit -m "My changes"

# ssubmit 會檢查是否有未提交的更改
# 如果有會拒絕提交
```

### 2. 檢查點命名規範
確保每個保存的檢查點都有獨特的名稱，包含時間戳和 git hash：
```python
# 不好
torch.save(model.state_dict(), 'checkpoints/model.pth')

# 好
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
filename = f'checkpoints/model_{timestamp}_{git_hash}.pth'
torch.save(model.state_dict(), filename)
```

### 3. 數據目錄的軟連接
共享目錄使用軟連接，確保：
- ✅ 可以安全地讀取和附加文件
- ❌ 不要刪除或移動整個目錄（會影響其他作業）
- ❌ 避免在軟連接上進行強制刪除操作

### 4. 虛擬環境配置
- 虛擬環境會被共享，所以使用 `ssubmit` 時應該確保它是合適的環境
- 或者在命令中指定激活虛擬環境：`ssubmit 'source .venv/bin/activate && python train.py'`
- 不同的 Python 版本或依賴可能不兼容，需要小心

### 5. 日誌位置
作業日誌自動保存到：
```
$HOME/log/TIMESTAMP_GIT_HASH.out
```

查看日誌：
```bash
tail -f ~/log/20250114_153022_a1b2c3d.out
```

### 6. 快照清理
快照存儲在：
```
$HOME/snapshots/TIMESTAMP_GIT_HASH/
```

作業完成後可以手動清理（但共享目錄的軟連接會保留）：
```bash
rm -rf ~/snapshots/TIMESTAMP_GIT_HASH/
```

## 工作流示例

```bash
# 1. 開發並提交代碼
git add train.py
git commit -m "Add new training script"

# 2. 提交作業（自動創建代碼快照）
ssubmit --gres=gpu:h100:1 'python train.py --epochs=100'

# 3. 檢查作業狀態
squeue

# 4. 查看日誌
tail -f ~/log/20250114_153022_a1b2c3d.out

# 5. 繼續開發（不影響運行中的作業）
git checkout -b new-feature
# ... 做出更改 ...
git commit -m "Try new approach"
ssubmit --gres=gpu:h100:1 'python train.py --epochs=100'  # 新快照，獨立運行
```

## 故障排除

### 錯誤：Dirty worktree detected
```
Dirty worktree detected. Please commit your changes first.
```
**解決方案**：提交或放棄所有更改
```bash
git add .
git commit -m "Save current state"
# 或
git checkout .  # 放棄更改
```

### 錯誤：Git could not be found
**解決方案**：安裝 Git
```bash
# Ubuntu/Debian
sudo apt-get install git

# macOS
brew install git
```

### 作業未啟動或日誌為空
**檢查清單**：
1. SLURM 服務是否運行中（`sinfo`）
2. 分區是否存在和可用（`sinfo`）
3. GPU 是否可用（`sinfo -p <partition> --gres`）
4. 檢查 SLURM 日誌：`cat ~/log/<job_id>.out`
