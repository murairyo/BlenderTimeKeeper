bl_info = {
    "name": "TimeKeeper - 作業時間計測",
    "author": "TimeKeeper Developer",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Status Bar",
    "description": "Blenderの作業時間を自動計測し、ステータスバーに表示します",
    "category": "System",
}

import bpy
import time
from bpy.app.handlers import persistent
from bpy.props import FloatProperty
from bpy.types import PropertyGroup

# デバッグ設定
DEBUG_MODE = True  # 修正後の動作確認のためTrueに変更

def debug_print(message):
    """デバッグ出力を制御する関数"""
    if DEBUG_MODE:
        print(message)

def error_print(message):
    """エラーメッセージは常に表示"""
    print(message)


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
        self.modal_operator_running = False  # モーダルオペレーターの実行状態を追跡
        self.last_update_time = 0  # 最後に累積時間を更新した時刻
        self.update_interval = 10.0  # 10秒間隔で累積時間を更新
        
    def reset(self):
        """アドオン再読み込み時のリセット処理"""
        debug_print("TimeKeeper: Resetting manager state")
        self.stop_session()
        self.modal_operator_running = False
        self.last_update_time = 0
        
    def start_session(self):
        """作業セッションを開始"""
        if not self.is_running:
            # コンテキストの安全性をチェック
            try:
                if not hasattr(bpy.context.scene, 'timekeeper_data'):
                    debug_print("TimeKeeper: timekeeper_data not found in scene")
                    return False
                    
                data = bpy.context.scene.timekeeper_data
                current_time = time.time()
                data.session_start_time = current_time
                self.last_update_time = current_time  # 定期更新の基準時刻を設定
                self.is_running = True
                self._register_timer()
                return True
            except Exception as e:
                debug_print(f"TimeKeeper: Failed to start session: {e}")
                return False
        return True
    
    def stop_session(self):
        """作業セッションを停止"""
        if self.is_running:
            try:
                # セッション停止時は最後の時間更新を行う
                current_time = time.time()
                if self.last_update_time > 0:
                    data = bpy.context.scene.timekeeper_data
                    # 最後の更新から現在までの時間を累積に追加
                    final_duration = current_time - self.last_update_time
                    data.total_time += final_duration
                    debug_print(f"TimeKeeper: Final update on stop - Added {final_duration:.1f}s, Total: {data.total_time:.1f}s")
            except Exception as e:
                debug_print(f"TimeKeeper: Error updating time on stop: {e}")
            self.is_running = False
            self.last_update_time = 0
            self._unregister_timer()
    
    def _update_total_time(self):
        """累積時間を更新"""
        if self.is_running:
            try:
                data = bpy.context.scene.timekeeper_data
                current_time = time.time()
                session_duration = current_time - data.session_start_time
                data.total_time += session_duration
                data.session_start_time = current_time
            except Exception as e:
                debug_print(f"TimeKeeper: Error in _update_total_time: {e}")
    
    def _periodic_update_total_time(self):
        """定期的な累積時間更新（10秒間隔）"""
        if not self.is_running:
            return
            
        try:
            current_time = time.time()
            # 10秒間隔で累積時間を更新
            if current_time - self.last_update_time >= self.update_interval:
                data = bpy.context.scene.timekeeper_data
                if data.session_start_time > 0:
                    # 前回の更新から今回までの時間を累積に追加
                    update_duration = current_time - self.last_update_time
                    data.total_time += update_duration
                    self.last_update_time = current_time
                    # session_start_timeは変更しない（表示計算用）
                    debug_print(f"TimeKeeper: Periodic update - Added {update_duration:.1f}s, Total: {data.total_time:.1f}s")
        except Exception as e:
            debug_print(f"TimeKeeper: Error in periodic update: {e}")
    
    def get_current_total_time(self):
        """現在の累積時間を取得（現在のセッション時間を含む）"""
        try:
            data = bpy.context.scene.timekeeper_data
            total = data.total_time
            
            if self.is_running and data.session_start_time > 0 and self.last_update_time > 0:
                # 最後の定期更新から現在までの時間を追加
                current_time = time.time()
                since_last_update = current_time - self.last_update_time
                total += since_last_update
                
            return total
        except Exception as e:
            debug_print(f"TimeKeeper: Error getting current time: {e}")
            return 0.0
    
    def _register_timer(self):
        """タイマーを登録"""
        if self.timer is None:
            try:
                self.timer = bpy.app.timers.register(
                    self._timer_callback, 
                    first_interval=0.3, 
                    persistent=True
                )
                debug_print("TimeKeeper: Main timer registered with 0.3s interval")
            except Exception as e:
                debug_print(f"TimeKeeper: Failed to register timer: {e}")
    
    def _unregister_timer(self):
        """タイマーの登録を解除"""
        if self.timer is not None:
            try:
                bpy.app.timers.unregister(self.timer)
                debug_print("TimeKeeper: Main timer unregistered")
            except Exception as e:
                debug_print(f"TimeKeeper: Error unregistering timer: {e}")
            finally:
                self.timer = None
    
    def _timer_callback(self):
        """タイマーコールバック関数"""
        try:
            # 安全性チェック
            if not self.is_running:
                debug_print("TimeKeeper: Timer callback called but session not running")
                return None  # タイマーを停止
            
            # 定期的な累積時間更新を実行
            self._periodic_update_total_time()
            
            # コンテキストの有効性をチェック
            if not hasattr(bpy.context, 'window_manager') or not bpy.context.window_manager:
                return 0.3  # コンテキストが無効でも継続
            
            current_time = self.get_current_total_time()
            # デバッグ出力を減らす（詳細が必要な場合のみ有効化）
            # debug_print(f"TimeKeeper: Main timer callback - Current time: {current_time:.1f}s")
            
            # 安全なUI更新
            updated = False
            try:
                # エリアのタグ更新（最も安全）
                for window in bpy.context.window_manager.windows:
                    if window and hasattr(window, 'screen') and window.screen:
                        for area in window.screen.areas:
                            if area.type == 'STATUSBAR':
                                area.tag_redraw()
                                updated = True
                                # リージョンの更新は軽量なので継続
                                for region in area.regions:
                                    if region.type == 'HEADER':
                                        region.tag_redraw()
                
                # redraw_timerは副作用の少ない方法のみ使用
                if updated:
                    try:
                        # 最も軽量で安全な再描画方式
                        bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                    except:
                        # フォールバック：強制的だが確実
                        try:
                            bpy.ops.wm.redraw_timer(type='DRAW_WIN', iterations=1)
                        except:
                            # フレーム設定は削除（副作用があるため）
                            pass
                
            except Exception as e:
                debug_print(f"TimeKeeper: Error in timer callback: {e}")
                # 最小限のフォールバック
                try:
                    if hasattr(bpy.context, 'screen') and bpy.context.screen:
                        for area in bpy.context.screen.areas:
                            if area.type == 'STATUSBAR':
                                area.tag_redraw()
                except:
                    pass
        
        except Exception as e:
            debug_print(f"TimeKeeper: Critical error in timer callback: {e}")
            # 重大なエラーが発生した場合はタイマーを停止
            return None
        
        return 0.3  # 0.3秒間隔で継続


# グローバルマネージャーインスタンス
timekeeper_manager = TimeKeeperManager()


class TIMEKEEPER_OT_Modal(bpy.types.Operator):
    """モーダルオペレーター：バックグラウンドでUI更新を保証"""
    bl_idname = "timekeeper.modal_update"
    bl_label = "TimeKeeper Modal Update"
    
    _timer = None
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # 軽量なデバッグ（必要時のみ有効化）
            # print("TimeKeeper: Modal timer callback executed")
            
            try:
                # セッションが停止していたらモーダルを終了
                if not timekeeper_manager.is_running:
                    debug_print("TimeKeeper: Modal operator stopping - session ended")
                    return self.cancel(context)
                
                # 安全なUI更新
                try:
                    # STATUSBARエリアの更新
                    updated = False
                    for window in context.window_manager.windows:
                        if window and hasattr(window, 'screen') and window.screen:
                            for area in window.screen.areas:
                                if area.type == 'STATUSBAR':
                                    area.tag_redraw()
                                    updated = True
                                    for region in area.regions:
                                        if region.type == 'HEADER':
                                            region.tag_redraw()
                    
                    # 軽量な強制更新
                    if updated:
                        try:
                            bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                        except:
                            # フォールバック
                            try:
                                bpy.ops.wm.redraw_timer(type='DRAW_WIN', iterations=1)
                            except:
                                # フレーム設定は削除（副作用のため）
                                pass
                            
                except Exception as e:
                    debug_print(f"TimeKeeper: Modal update error: {e}")
                    # 最小限のフォールバック
                    try:
                        if hasattr(context, 'screen') and context.screen:
                            for area in context.screen.areas:
                                if area.type == 'STATUSBAR':
                                    area.tag_redraw()
                    except:
                        pass
                
            except Exception as e:
                debug_print(f"TimeKeeper: Critical modal error: {e}")
                return self.cancel(context)
            
            return {'PASS_THROUGH'}
        
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        # 重複実行を防ぐ
        if timekeeper_manager.modal_operator_running:
            debug_print("TimeKeeper: Modal operator already running, skipping")
            return {'CANCELLED'}
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)  # 間隔を0.5秒に戻す
        wm.modal_handler_add(self)
        timekeeper_manager.modal_operator_running = True
        debug_print("TimeKeeper: Modal timer set to 0.5s interval")
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
        timekeeper_manager.modal_operator_running = False
        debug_print("TimeKeeper: Modal operator cancelled")
        return {'CANCELLED'}


def draw_timekeeper_header(self, context):
    """StatusBarに時間を描画する関数"""
    try:
        layout = self.layout
        
        # マネージャーの状態をチェック
        if not timekeeper_manager:
            return
        
        # 現在の累積時間を安全に取得
        total_seconds = timekeeper_manager.get_current_total_time()
        
        # 異常値のチェック
        if total_seconds < 0:
            total_seconds = 0
        elif total_seconds > 999999:  # 約11日以上
            total_seconds = 999999
        
        # 時間をフォーマット
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        # 24時間を超える場合の表示調整
        if hours > 99:
            time_text = f"作業時間: {hours}:{minutes:02d}:{seconds:02d}"
        else:
            time_text = f"作業時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # StatusBarに直接表示（separator_spacerは不要）
        layout.label(text=time_text, icon='TIME')
        
    except Exception as e:
        # エラーが発生した場合は簡単なフォールバック表示
        try:
            layout = self.layout
            layout.label(text="作業時間: --:--:--", icon='TIME')
        except:
            # 最悪の場合は何も表示しない
            pass


@persistent
def timekeeper_load_pre_handler(dummy):
    """ファイル読み込み前のハンドラー"""
    debug_print("TimeKeeper: Load pre handler called")
    try:
        timekeeper_manager.stop_session()
    except Exception as e:
        debug_print(f"TimeKeeper: Error in load pre handler: {e}")


@persistent
def timekeeper_load_post_handler(dummy):
    """ファイル読み込み後のハンドラー"""
    debug_print("TimeKeeper: Load post handler called")
    
    try:
        # データが存在しない場合は初期化を待つ
        if not hasattr(bpy.context.scene, 'timekeeper_data'):
            debug_print("TimeKeeper: timekeeper_data not found after load")
            return
        
        # 既存のセッションをリセット
        timekeeper_manager.reset()
        
        # 新しいセッションを開始
        if timekeeper_manager.start_session():
            debug_print("TimeKeeper: Session restarted after file load")
        else:
            debug_print("TimeKeeper: Failed to restart session after file load")
            
    except Exception as e:
        debug_print(f"TimeKeeper: Error in load post handler: {e}")


@persistent
def timekeeper_save_pre_handler(dummy):
    """ファイル保存前のハンドラー"""
    debug_print("TimeKeeper: Save pre handler called")
    
    try:
        # セーブ時は時間の加算はしない（重複計算を防ぐため）
        # session_start_timeのみをリセットして継続的な計測を保証
        if timekeeper_manager.is_running:
            # コンテキストの安全性をチェック
            if not hasattr(bpy.context.scene, 'timekeeper_data'):
                debug_print("TimeKeeper: Save - timekeeper_data not found")
                return
                
            data = bpy.context.scene.timekeeper_data
            current_time = time.time()
            
            if data.session_start_time > 0:
                # 現在のセッション時間を表示のみ（加算はしない）
                session_duration = current_time - data.session_start_time
                debug_print(f"TimeKeeper: Save - Current session: {session_duration:.1f}s, Total: {data.total_time:.1f}s")
                
                # セッション継続のためstart_timeを現在時刻にリセット
                # （時間の加算はタイマーに任せる）
                data.session_start_time = current_time
                debug_print("TimeKeeper: Save - Session time reset for continuity")
            else:
                debug_print("TimeKeeper: Save - No active session")
        else:
            debug_print("TimeKeeper: Save - Timer not running")
            
    except Exception as e:
        debug_print(f"TimeKeeper: Error in save pre handler: {e}")


# グローバル変数
startup_timer_handle = None  # startupタイマーの管理用


def timekeeper_startup():
    """アドオン起動時の処理"""
    global startup_timer_handle
    debug_print("TimeKeeper: Starting up...")
    
    try:
        # 初期データが存在しない場合は作成を待つ
        if not hasattr(bpy.context.scene, 'timekeeper_data'):
            debug_print("TimeKeeper: timekeeper_data not found, skipping startup")
            return
        
        # 既存のセッションをクリーンアップ
        timekeeper_manager.reset()
        
        data = bpy.context.scene.timekeeper_data
        if data.total_time == 0 and data.session_start_time == 0:
            debug_print("TimeKeeper: New file detected")
        
        # セッション開始
        if timekeeper_manager.start_session():
            debug_print("TimeKeeper: Session started successfully")
            
            # モーダルオペレーターを起動（重複チェック付き）
            try:
                if not timekeeper_manager.modal_operator_running:
                    bpy.ops.timekeeper.modal_update()
                    debug_print("TimeKeeper: Modal operator started")
                else:
                    debug_print("TimeKeeper: Modal operator already running")
            except Exception as e:
                debug_print(f"TimeKeeper: Failed to start modal operator: {e}")
        else:
            debug_print("TimeKeeper: Failed to start session")
            
    except Exception as e:
        debug_print(f"TimeKeeper: Startup error: {e}")
    finally:
        # startupタイマーをクリアして一回のみ実行を保証
        startup_timer_handle = None


def register():
    """アドオン登録"""
    global startup_timer_handle
    
    debug_print("TimeKeeper: Registering addon...")
    
    # 既存の状態をクリーンアップ
    try:
        timekeeper_manager.reset()
    except:
        pass
    
    # クラスを登録
    bpy.utils.register_class(TimeKeeperData)
    bpy.utils.register_class(TIMEKEEPER_OT_Modal)
    
    # プロパティをシーンに追加
    bpy.types.Scene.timekeeper_data = bpy.props.PointerProperty(type=TimeKeeperData)
    
    # ヘッダーに描画関数を追加
    bpy.types.STATUSBAR_HT_header.append(draw_timekeeper_header)
    
    # ハンドラーを登録（重複チェック付き）
    if timekeeper_load_pre_handler not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(timekeeper_load_pre_handler)
    
    if timekeeper_load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(timekeeper_load_post_handler)
    
    if timekeeper_save_pre_handler not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(timekeeper_save_pre_handler)
    
    # 起動処理を少し遅らせて実行（一回のみ）
    if startup_timer_handle is None:
        startup_timer_handle = bpy.app.timers.register(
            timekeeper_startup, 
            first_interval=0.1
        )
        debug_print("TimeKeeper: Startup timer registered")


def unregister():
    """アドオン登録解除"""
    global startup_timer_handle
    
    debug_print("TimeKeeper: Unregistering addon...")
    
    # startupタイマーを停止
    if startup_timer_handle is not None:
        try:
            bpy.app.timers.unregister(startup_timer_handle)
            debug_print("TimeKeeper: Startup timer unregistered")
        except:
            pass
        startup_timer_handle = None
    
    # マネージャーを停止
    timekeeper_manager.reset()
    
    # ヘッダーから描画関数を削除
    try:
        bpy.types.STATUSBAR_HT_header.remove(draw_timekeeper_header)
    except:
        pass
    
    # ハンドラーを削除
    if timekeeper_load_pre_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(timekeeper_load_pre_handler)
    
    if timekeeper_load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(timekeeper_load_post_handler)
    
    if timekeeper_save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(timekeeper_save_pre_handler)
    
    # プロパティを削除
    try:
        del bpy.types.Scene.timekeeper_data
    except:
        pass
    
    # クラスの登録を解除
    try:
        bpy.utils.unregister_class(TIMEKEEPER_OT_Modal)
        bpy.utils.unregister_class(TimeKeeperData)
    except:
        pass
    
    debug_print("TimeKeeper: Unregistration complete")


if __name__ == "__main__":
    register() 