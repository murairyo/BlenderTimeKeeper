bl_info = {
    "name": "TimeKeeper - 作業時間計測",
    "author": "TimeKeeper Developer",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Top Bar > Right Side",
    "description": "Blenderの作業時間を自動計測し、トップバーに表示します",
    "category": "System",
}

import bpy
import time
from bpy.app.handlers import persistent
from bpy.props import FloatProperty
from bpy.types import PropertyGroup


class TimeKeeperData(PropertyGroup):
    """作業時間データを保存するプロパティグループ"""
    total_time: FloatProperty(
        name="Total Time",
        description="累積作業時間（秒）",
        default=0.0,
        min=0.0
    )
    
    session_start_time: FloatProperty(
        name="Session Start Time",
        description="現在のセッション開始時刻",
        default=0.0,
        min=0.0
    )


class TimeKeeperManager:
    """作業時間管理の中核クラス"""
    
    def __init__(self):
        self.is_running = False
        self.timer = None
        self.last_display_second = -1  # 最後に表示した秒数を記録
        
    def start_session(self):
        """作業セッションを開始"""
        if not self.is_running:
            data = bpy.context.scene.timekeeper_data
            data.session_start_time = time.time()
            self.is_running = True
            self._register_timer()
    
    def stop_session(self):
        """作業セッションを停止"""
        if self.is_running:
            self._update_total_time()
            self.is_running = False
            self._unregister_timer()
    
    def _update_total_time(self):
        """累積時間を更新"""
        if self.is_running:
            data = bpy.context.scene.timekeeper_data
            current_time = time.time()
            session_duration = current_time - data.session_start_time
            data.total_time += session_duration
            data.session_start_time = current_time
    
    def get_current_total_time(self):
        """現在の累積時間を取得（現在のセッション時間を含む）"""
        data = bpy.context.scene.timekeeper_data
        total = data.total_time
        
        if self.is_running and data.session_start_time > 0:
            current_session = time.time() - data.session_start_time
            total += current_session
            
        return total
    
    def _register_timer(self):
        """タイマーを登録"""
        if self.timer is None:
            self.timer = bpy.app.timers.register(self._timer_callback, first_interval=0.1)
    
    def _unregister_timer(self):
        """タイマーの登録を解除"""
        if self.timer is not None:
            try:
                bpy.app.timers.unregister(self.timer)
            except:
                pass
            self.timer = None
    
    def _timer_callback(self):
        """タイマーコールバック関数"""
        # より確実なUI更新をトリガー
        try:
            # 全てのウィンドウのTOPBARエリアを更新
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TOPBAR':
                        area.tag_redraw()
        except:
            # フォールバック: 現在のコンテキストで更新を試行
            try:
                for area in bpy.context.screen.areas:
                    if area.type == 'TOPBAR':
                        area.tag_redraw()
            except:
                pass
        
        return 0.1  # 0.1秒後に再実行（10回/秒でスムーズな更新）


# グローバルマネージャーインスタンス
timekeeper_manager = TimeKeeperManager()


def draw_timekeeper_header(self, context):
    """ヘッダーに時間を描画する関数"""
    layout = self.layout
    
    # 現在の累積時間を取得
    total_seconds = timekeeper_manager.get_current_total_time()
    
    # 時間をフォーマット
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    time_text = f"作業時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # 右端に表示するためのスペーサー
    layout.separator_spacer()
    
    # テキストを表示
    layout.label(text=time_text, icon='TIME')


@persistent
def timekeeper_load_pre_handler(dummy):
    """ファイル読み込み前のハンドラー"""
    timekeeper_manager.stop_session()


@persistent
def timekeeper_load_post_handler(dummy):
    """ファイル読み込み後のハンドラー"""
    # データが存在しない場合は初期化
    if not hasattr(bpy.context.scene, 'timekeeper_data'):
        return
    
    # 新しいセッションを開始
    timekeeper_manager.start_session()


@persistent
def timekeeper_save_pre_handler(dummy):
    """ファイル保存前のハンドラー"""
    # 保存前に累積時間を更新
    timekeeper_manager._update_total_time()


def timekeeper_startup():
    """アドオン起動時の処理"""
    # 初期データが存在しない場合は作成
    if hasattr(bpy.context.scene, 'timekeeper_data'):
        data = bpy.context.scene.timekeeper_data
        if data.total_time == 0 and data.session_start_time == 0:
            # 新規ファイルの場合
            pass
    
    # セッション開始
    timekeeper_manager.start_session()


def register():
    """アドオン登録"""
    bpy.utils.register_class(TimeKeeperData)
    
    # プロパティをシーンに追加
    bpy.types.Scene.timekeeper_data = bpy.props.PointerProperty(type=TimeKeeperData)
    
    # ヘッダーに描画関数を追加
    bpy.types.TOPBAR_HT_upper_bar.append(draw_timekeeper_header)
    
    # ハンドラーを登録
    if timekeeper_load_pre_handler not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(timekeeper_load_pre_handler)
    
    if timekeeper_load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(timekeeper_load_post_handler)
    
    if timekeeper_save_pre_handler not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(timekeeper_save_pre_handler)
    
    # 起動処理を少し遅らせて実行
    bpy.app.timers.register(timekeeper_startup, first_interval=0.1)


def unregister():
    """アドオン登録解除"""
    # マネージャーを停止
    timekeeper_manager.stop_session()
    
    # ヘッダーから描画関数を削除
    bpy.types.TOPBAR_HT_upper_bar.remove(draw_timekeeper_header)
    
    # ハンドラーを削除
    if timekeeper_load_pre_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(timekeeper_load_pre_handler)
    
    if timekeeper_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(timekeeper_load_post_handler)
    
    if timekeeper_save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(timekeeper_save_pre_handler)
    
    # プロパティを削除
    del bpy.types.Scene.timekeeper_data
    
    # クラスの登録を解除
    bpy.utils.unregister_class(TimeKeeperData)


if __name__ == "__main__":
    register() 