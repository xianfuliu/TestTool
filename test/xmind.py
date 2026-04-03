import sys
import json
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import math

class MindMapNode(QGraphicsItem):
    """思维导图节点类"""
    
    def __init__(self, text="新节点", parent_node=None, scene=None, node_id=None):
        super().__init__()
        self.text = text
        self.parent_node = parent_node
        self.child_nodes = []
        self.node_id = node_id if node_id else str(id(self))
        self.level = 0 if parent_node is None else parent_node.level + 1
        
        # 节点属性
        self.width = 120
        self.height = 40
        self.corner_radius = 8
        self.padding = 10
        
        # 颜色设置
        self.colors = [
            QColor(66, 133, 244),   # 蓝色
            QColor(52, 168, 83),    # 绿色
            QColor(251, 188, 5),    # 黄色
            QColor(234, 67, 53),    # 红色
            QColor(171, 71, 188),   # 紫色
            QColor(255, 112, 67),   # 橙色
        ]
        self.node_color = self.colors[self.level % len(self.colors)]
        self.text_color = QColor(Qt.white)
        self.border_color = QColor(Qt.darkGray)
        self.hover_color = QColor(255, 255, 255, 50)
        
        # 状态
        self.is_hovered = False
        self.is_expanded = True
        
        # 模式管理：使用枚举值来清晰管理三种模式
        self._mode = 'normal'  # normal: 未选中, selected: 选中, editing: 编辑
        
        # 兼容原有属性（用于外部访问）
        self.is_selected = False
        self.is_editing = False
        
        # 设置标志
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        # 确保整个形状区域都可以点击（不仅仅是边框）
        self.setFlag(QGraphicsItem.ItemClipsToShape, False)
        self.setFlag(QGraphicsItem.ItemClipsChildrenToShape, False)
        
        # 模式管理方法
        self._mode = 'normal'  # normal: 未选中, selected: 选中, editing: 编辑
        
        # 监听选择状态变化
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        
        # 文本编辑控件
        self.text_edit = None
        self.text_item = None
        
        # 如果有关联的场景，添加文本图形项
        if scene:
            self.add_text_item(scene)
        
        # 初始位置
        if parent_node:
            self.setPos(parent_node.scenePos() + QPointF(150, 0))
    
    def add_text_item(self, scene):
        """添加文本图形项"""
        self.text_item = QGraphicsTextItem(self.text, self)
        self.text_item.setDefaultTextColor(self.text_color)
        font = QFont("微软雅黑" if sys.platform == "win32" else "Arial")
        font.setPointSize(10)
        font.setBold(True)
        self.text_item.setFont(font)
        self.text_item.setTextInteractionFlags(Qt.NoTextInteraction)
        self.text_item.setPos(5, 5)
        
        # 调整文本宽度
        text_width = self.text_item.boundingRect().width()
        self.width = max(120, text_width + 20)
        self.text_item.setTextWidth(self.width - 10)
    
    def set_mode(self, mode):
        """设置节点模式"""
        if mode not in ['normal', 'selected', 'editing']:
            return
            
        self._mode = mode
        
        # 同步兼容属性
        self.is_selected = (mode == 'selected')
        self.is_editing = (mode == 'editing')
        
        # 更新显示
        self.update()
    
    def get_mode(self):
        """获取当前模式"""
        return self._mode
    
    def boundingRect(self):
        """定义节点的边界矩形"""
        return QRectF(0, 0, self.width, self.height)
    
    def shape(self):
        """定义节点的形状（用于命中检测）"""
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.height, self.corner_radius, self.corner_radius)
        return path
    
    def contains(self, point):
        """检测点是否在节点内部（确保整个矩形区域都可点击）"""
        # 使用与shape方法一致的圆角矩形检测，确保整个节点区域都可点击
        return self.shape().contains(point)
    
    def paint(self, painter, option, widget=None):
        """绘制节点"""
        # 保存画笔状态
        painter.save()
        
        # 设置抗锯齿
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制节点背景 - 根据模式选择样式
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, self.node_color.lighter(110))
        gradient.setColorAt(1, self.node_color)
        painter.setBrush(QBrush(gradient))
        
        # 根据模式设置边框样式
        if self._mode == 'editing':
            # 编辑模式：细边框，不需要橙色边框
            painter.setPen(QPen(self.border_color.lighter(120), 1))  # 细边框
        elif self._mode == 'selected':
            # 选中状态：橙色外边框
            painter.setPen(QPen(QColor(255, 152, 0), 3))  # 橙色边框
        else:
            # 未选中模式：细边框
            painter.setPen(QPen(self.border_color.lighter(120), 1))  # 细边框
        
        # 绘制圆角矩形
        painter.drawRoundedRect(0, 0, int(self.width), int(self.height), 
                               int(self.corner_radius), int(self.corner_radius))
        
        # 鼠标悬停效果（只在普通模式下显示）
        if self.is_hovered and self._mode == 'normal':
            painter.setBrush(QBrush(self.hover_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, int(self.width), int(self.height), 
                                   int(self.corner_radius), int(self.corner_radius))
        
        # 恢复画笔状态
        painter.restore()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            print(f"节点鼠标按下: 当前模式={self._mode}, 文本={self.text}")
            # 如果正在编辑，单击退出编辑模式
            if self._mode == 'editing':
                self.finish_editing()
                return
            
            # 设置选中模式
            print("节点: 设置选中模式")
            self.set_mode('selected')
            self.setSelected(True)
            print(f"节点: 设置完成, 模式={self._mode}, 选中={self.isSelected()}")
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        """处理项目状态变化"""
        if change == QGraphicsItem.ItemSelectedChange:
            print(f"节点itemChange: {self.text} 选中状态变化: value={bool(value)}, 当前模式={self._mode}")
            # 同步选择状态到模式管理系统
            if bool(value):
                # 只有在不是编辑模式时才设置为选中模式
                if self._mode != 'editing':
                    self.set_mode('selected')
                    print(f"节点itemChange: {self.text} 设置为选中模式")
            else:
                # 取消选中时，如果不是编辑模式，则返回普通模式
                if self._mode != 'editing':
                    self.set_mode('normal')
                    print(f"节点itemChange: {self.text} 设置为普通模式")
        return super().itemChange(change, value)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件 - 编辑文本"""
        if event.button() == Qt.LeftButton:
            self.start_editing()
    
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        self.is_hovered = True
        self.update()
        self.setCursor(Qt.PointingHandCursor)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def start_editing(self):
        """开始编辑文本"""
        if self._mode == 'editing':
            return
        
        # 设置编辑模式（编辑模式优先级最高）
        self.set_mode('editing')
        
        # 创建文本编辑控件
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.text)
        self.text_edit.setFixedSize(int(self.width - 10), int(self.height - 10))
        
        # 创建代理控件
        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.text_edit)
        self.proxy.setPos(5, 5)
        
        # 连接焦点失去信号
        self.text_edit.focusOutEvent = self.text_edit_focus_out
        
        # 隐藏文本图形项
        if self.text_item:
            self.text_item.hide()
        
        # 设置编辑控件样式
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid rgba(255, 255, 255, 100);
                background: rgba(0, 0, 0, 50);
                color: white;
                font-weight: bold;
                font-size: 10pt;
                selection-background-color: rgba(255, 255, 255, 100);
            }
        """)
        
        # 焦点进入编辑框
        self.text_edit.setFocus()
        self.text_edit.selectAll()  # 自动全选文本
        
        # 连接回车键信号（使用 returnPressed 信号）
        # 注意：QTextEdit 没有 returnPressed 信号，所以我们需要捕获键盘事件
        self.text_edit.keyPressEvent = self.text_edit_key_press
        
        # 启用文本交互
        self.text_edit.setTextInteractionFlags(Qt.TextEditorInteraction)
        
        self.update()

    def text_edit_key_press(self, event):
        """处理文本编辑框的键盘事件"""
        if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
            # Ctrl+Enter 完成编辑
            self.finish_editing()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter 插入换行
                QTextEdit.keyPressEvent(self.text_edit, event)
            else:
                # Enter 确认输入
                self.finish_editing()
        elif event.key() == Qt.Key_Escape:
            # ESC 取消编辑
            self.cancel_editing()
        else:
            # 正确调用父类的keyPressEvent方法
            QTextEdit.keyPressEvent(self.text_edit, event)

    def text_edit_focus_out(self, event):
        """处理文本编辑框焦点失去事件"""
        self.finish_editing()
        # 调用原始的焦点失去事件处理
        # 由于我们重写了focusOutEvent，这里不需要调用父类方法

    def cancel_editing(self):
        """取消文本编辑"""
        if self._mode != 'editing' or not self.text_edit:
            return
        
        # 清理编辑控件
        if self.text_edit:
            self.text_edit.deleteLater()
            self.text_edit = None
        
        if self.proxy:
            self.scene().removeItem(self.proxy)
            self.proxy = None
        
        # 显示原来的文本
        if self.text_item:
            self.text_item.show()
        
        # 恢复为普通模式
        self.set_mode('normal')

    def finish_editing(self):
        """完成文本编辑"""
        if self._mode != 'editing' or not self.text_edit:
            return
        
        new_text = self.text_edit.toPlainText().strip()
        if new_text:
            self.text = new_text
            
            # 更新文本图形项
            if self.text_item:
                self.text_item.setPlainText(self.text)
                self.text_item.show()
                
                # 调整节点大小
                text_width = self.text_item.boundingRect().width()
                self.width = max(120, text_width + 20)
                self.text_item.setTextWidth(self.width - 10)
        
        # 清理编辑控件
        if self.text_edit:
            self.text_edit.deleteLater()
            self.text_edit = None
        
        if self.proxy:
            self.scene().removeItem(self.proxy)
            self.proxy = None
        
        # 恢复为普通模式
        self.set_mode('normal')
        
        # 更新所有连接线
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, MindMapConnection):
                    item.update_path()
    

    
    def add_child(self, text="子节点"):
        """添加子节点 - 动态调整兄弟节点间距避免子节点重叠"""
        print(f"=== 在节点 '{self.text}' 上添加子节点 ===")
        
        # 创建新节点
        child = MindMapNode(text, parent_node=self, scene=self.scene())
        print(f"创建子节点: {child.text}, 层级={child.level}")
        
        # 添加到子节点列表
        self.child_nodes.append(child)
        print(f"添加到子节点列表，当前子节点数量: {len(self.child_nodes)}")
        
        # 添加到场景
        if self.scene():
            self.scene().addItem(child)
            print(f"子节点已添加到场景")
            
            # 创建连接线
            connection = MindMapConnection(self, child)
            self.scene().addItem(connection)
            
            # 设置焦点到新创建的子节点
            if self.scene() and self.scene().views():
                self.scene().views()[0].setFocus()
        
        # 递归向上重新布局，避免位置重叠冲突
        self.layout_upward_recursive()
        
        return child
    
    def layout_upward_recursive(self):
        """递归向上重新布局，避免位置重叠冲突"""
        print(f"=== 开始递归向上布局，从节点 '{self.text}' 开始 ===")
        
        # 从当前节点开始，向上递归到根节点
        current_node = self
        while current_node:
            print(f"布局节点: {current_node.text}, 层级={current_node.level}")
            
            # 如果当前节点有父节点，需要重新布局父节点的所有子节点
            if current_node.parent_node:
                # 重新布局父节点的所有子节点（包括当前节点的兄弟节点）
                current_node.parent_node.layout_children_smart()
            else:
                # 如果是根节点，重新布局所有子节点
                current_node.layout_children_smart()
            
            # 向上移动到父节点
            current_node = current_node.parent_node
        
        print(f"=== 递归向上布局完成 ===")
    
    def layout_children_simple(self):
        """简单布局所有子节点 - 确保不重叠"""
        if not self.child_nodes or not self.is_expanded:
            return
        
        print(f"开始布局节点: {self.text}, 子节点数量: {len(self.child_nodes)}")
        
        # 基础参数
        level_spacing = 200  # 层级间距
        sibling_spacing = 80  # 兄弟节点间距
        
        # 计算对称分布
        child_count = len(self.child_nodes)
        center_index = (child_count - 1) / 2
        
        # 布局所有子节点
        for i, child in enumerate(self.child_nodes):
            # 计算对称分布的y位置
            y_offset = (i - center_index) * sibling_spacing
            
            # 设置子节点位置
            new_x = self.scenePos().x() + level_spacing
            new_y = self.scenePos().y() + y_offset
            child.setPos(new_x, new_y)
            print(f"布局子节点: {child.text} -> 位置({new_x:.1f}, {new_y:.1f})")
            
            # 递归布局子节点的子节点
            child.layout_children_simple()
    
    def layout_children_immediate(self):
        """立即布局所有子节点 - 简单有效的算法"""
        if not self.child_nodes or not self.is_expanded:
            return
        
        print(f"立即布局节点: {self.text}, 子节点数量: {len(self.child_nodes)}")
        
        # 基础参数
        level_spacing = 200  # 层级间距
        sibling_spacing = 80  # 兄弟节点间距
        
        # 计算对称分布
        child_count = len(self.child_nodes)
        center_index = (child_count - 1) / 2
        
        # 布局所有子节点
        for i, child in enumerate(self.child_nodes):
            # 计算对称分布的y位置
            y_offset = (i - center_index) * sibling_spacing
            
            # 设置子节点位置
            new_x = self.scenePos().x() + level_spacing
            new_y = self.scenePos().y() + y_offset
            child.setPos(new_x, new_y)
            print(f"布局子节点: {child.text} -> 位置({new_x:.1f}, {new_y:.1f})")
            
            # 递归布局子节点的子节点
            child.layout_children_immediate()
    
    def remove_child(self, child):
        """移除子节点"""
        if child in self.child_nodes:
            self.child_nodes.remove(child)
            
            # 从场景中移除
            if child.scene():
                # 移除子节点的所有连接线
                for item in child.scene().items():
                    if isinstance(item, MindMapConnection) and (item.start_node == child or item.end_node == child):
                        child.scene().removeItem(item)
                
                # 移除子节点
                child.scene().removeItem(child)
            
            # 重新布局
            self.layout_children()
    
    def layout_children(self):
        """布局子节点"""
        if not self.child_nodes or not self.is_expanded:
            return
        
        start_y = self.scenePos().y() - (len(self.child_nodes) * 60) / 2
        
        for i, child in enumerate(self.child_nodes):
            target_y = start_y + i * 60
            child.setPos(child.scenePos().x(), target_y)
            
            # 递归布局子节点的子节点
            child.layout_children()
    
    def layout_children_smart(self):
        """智能布局子节点 - 动态调整兄弟节点间距防止子节点重叠"""
        if not self.child_nodes or not self.is_expanded:
            print(f"布局跳过: {self.text} 没有子节点或未展开")
            return
        
        print(f"开始布局节点: {self.text}, 子节点数量: {len(self.child_nodes)}")
        
        # 基础参数
        level_spacing = 200  # 层级间距
        
        # 智能计算子节点间距，考虑节点高度和防重叠需求
        node_height = 40  # 节点高度
        base_sibling_spacing = node_height + 40  # 基础间距：节点高度 + 安全间距
        
        # 根据子节点数量动态调整间距
        child_count = len(self.child_nodes)
        
        # 子节点数量越多，间距越大（防止重叠）
        if child_count > 0:
            # 使用对数函数平滑增加间距，避免间距过大
            count_factor = math.log(child_count + 1) * 20
            sibling_spacing = base_sibling_spacing + count_factor
        else:
            sibling_spacing = base_sibling_spacing
        
        print(f"节点 {self.text} 的子节点数量: {child_count}, 子节点间距: {sibling_spacing:.1f}")
        
        # 计算当前节点的子节点数量
        child_count = len(self.child_nodes)
        
        # 对称分布：计算中心位置
        center_index = (child_count - 1) / 2
        
        # 关键改进：在布局父节点的子节点时，动态调整兄弟节点间距
        if self.parent_node and len(self.parent_node.child_nodes) > 1:
            # 计算所有兄弟节点的最大子节点数量
            max_children_count = 0
            for sibling in self.parent_node.child_nodes:
                if sibling.child_nodes and sibling.is_expanded:
                    max_children_count = max(max_children_count, len(sibling.child_nodes))
            
            # 动态调整兄弟节点间距，确保子节点有足够空间
            # 改进：根据兄弟节点的子节点数量动态调整间距
            dynamic_spacing = max(sibling_spacing, 100 + max_children_count * 30)
            
            # 获取当前节点在兄弟节点中的索引
            sibling_index = self.parent_node.child_nodes.index(self)
            
            # 计算兄弟节点间距调整因子
            sibling_adjustment = sibling_index * dynamic_spacing
            
            # 布局所有子节点
            for i, child in enumerate(self.child_nodes):
                # 计算对称分布的y位置
                y_offset = (i - center_index) * sibling_spacing
                
                # 设置子节点位置（考虑兄弟节点间距调整）
                new_x = self.scenePos().x() + level_spacing
                new_y = self.scenePos().y() + y_offset + sibling_adjustment
                child.setPos(new_x, new_y)
                print(f"动态间距布局子节点: {child.text} -> 位置({new_x:.1f}, {new_y:.1f}), 兄弟索引: {sibling_index}, 动态间距: {dynamic_spacing}")
                
                # 递归布局子节点的子节点
                child.layout_children_smart()
        else:
            # 如果没有兄弟节点或只有一个节点，使用原来的对称分布算法
            # 布局所有子节点
            for i, child in enumerate(self.child_nodes):
                # 计算对称分布的y位置
                y_offset = (i - center_index) * sibling_spacing
                
                # 设置子节点位置
                new_x = self.scenePos().x() + level_spacing
                new_y = self.scenePos().y() + y_offset
                child.setPos(new_x, new_y)
                print(f"布局子节点: {child.text} -> 位置({new_x:.1f}, {new_y:.1f})")
                
                # 递归布局子节点的子节点
                child.layout_children_smart()
        
        print(f"完成布局节点: {self.text}")
        
        # 新增：如果当前节点有兄弟节点，重新调整兄弟节点间距
        # 或者当前节点是根节点且有多个子节点（兄弟节点）
        if (self.parent_node and len(self.parent_node.child_nodes) > 1) or \
           (self.parent_node is None and len(self.child_nodes) > 1):
            self._adjust_sibling_spacing()
    
    def _get_max_child_depth(self):
        """获取当前节点下所有子节点的最大深度"""
        if not self.child_nodes:
            return 0
        
        max_depth = 0
        for child in self.child_nodes:
            # 当前子节点的深度（1层）加上其子节点的最大深度
            child_depth = 1 + child._get_max_child_depth()
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _adjust_sibling_spacing(self):
        """动态调整兄弟节点间距，避免子节点重叠"""
        # 确定要调整间距的节点列表
        if self.parent_node:
            # 当前节点有父节点，调整兄弟节点间距
            siblings = self.parent_node.child_nodes
            parent_y = self.parent_node.scenePos().y()
        else:
            # 当前节点是根节点，调整子节点间距
            siblings = self.child_nodes
            parent_y = self.scenePos().y()
        
        # 如果没有兄弟节点或只有一个节点，不需要调整
        if len(siblings) <= 1:
            return
        
        print(f"=== 开始动态调整兄弟节点间距，当前节点: {self.text} ===")
        
        # 计算所有兄弟节点的子节点信息
        total_children_count = 0
        max_child_depth = 0
        max_children_in_sibling = 0
        
        for sibling in siblings:
            if sibling.child_nodes and sibling.is_expanded:
                sibling_children_count = len(sibling.child_nodes)
                total_children_count += sibling_children_count
                max_children_in_sibling = max(max_children_in_sibling, sibling_children_count)
                # 计算每个兄弟节点的最大子节点深度
                sibling_depth = sibling._get_max_child_depth()
                max_child_depth = max(max_child_depth, sibling_depth)
        
        print(f"所有兄弟节点的子节点总数: {total_children_count}, 最大深度: {max_child_depth}, 单个兄弟最大子节点数: {max_children_in_sibling}")
        
        # 智能动态计算兄弟节点间距
        # 1. 基础间距：确保节点本身有足够空间
        base_spacing = 80  # 节点高度40px + 上下间距40px
        
        # 2. 子节点总数因子：考虑总体子节点数量
        children_total_factor = total_children_count * 15
        
        # 3. 最大子节点数因子：考虑单个兄弟节点的最大子节点数（重要！）
        children_max_factor = max_children_in_sibling * 25
        
        # 4. 深度因子：考虑子节点层级深度
        depth_spacing_factor = max_child_depth * 30
        
        # 5. 额外安全间距：防止边缘情况下的重叠
        safety_margin = 20
        
        # 综合计算动态间距（使用最大值策略确保足够间距）
        dynamic_spacing = max(
            base_spacing + children_total_factor,
            base_spacing + children_max_factor * 2,  # 单个兄弟节点子节点数更重要
            base_spacing + depth_spacing_factor
        ) + safety_margin
        
        print(f"动态计算的兄弟节点间距: {dynamic_spacing} (基础: {base_spacing}, 总数因子: {children_total_factor}, 最大数因子: {children_max_factor}, 深度因子: {depth_spacing_factor}, 安全间距: {safety_margin})")
        
        # 重新布局所有兄弟节点
        # 基于父节点的位置进行对称分布
        child_count = len(siblings)
        center_index = (child_count - 1) / 2
        
        for i, sibling in enumerate(siblings):
            # 计算对称分布的y位置
            y_offset = (i - center_index) * dynamic_spacing
            
            # 设置兄弟节点的新位置（保持x坐标不变，调整y坐标）
            new_x = sibling.scenePos().x()
            new_y = parent_y + y_offset
            sibling.setPos(new_x, new_y)
            
            print(f"调整兄弟节点位置: {sibling.text} -> 位置({new_x:.1f}, {new_y:.1f}), 索引: {i}")
            
            # 使用简单布局方法重新布局子节点，避免递归调用
            sibling.layout_children_immediate()
        
        print(f"=== 完成兄弟节点间距调整 ===")
    
    def layout_entire_mindmap_smart(self):
        """智能布局整个思维导图"""
        print("=== 开始整体布局思维导图 ===")
        
        # 找到根节点
        root = self
        while root.parent_node:
            root = root.parent_node
        
        print(f"找到根节点: {root.text}")
        
        # 从根节点开始布局
        root.layout_children_smart()
        
        print("=== 完成整体布局思维导图 ===")
    
    def itemChange(self, change, value):
        """项目变化事件（位置变化时更新连接线）"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # 更新父节点到本节点的连接线
            if self.parent_node and self.scene():
                for item in self.scene().items():
                    if isinstance(item, MindMapConnection) and item.end_node == self:
                        item.update_path()
            
            # 更新本节点到子节点的连接线
            for child in self.child_nodes:
                if self.scene():
                    for item in self.scene().items():
                        if isinstance(item, MindMapConnection) and item.start_node == self and item.end_node == child:
                            item.update_path()
            
            # 重新布局子节点
            self.layout_children()
        
        return super().itemChange(change, value)
    
    def to_dict(self):
        """转换为字典（用于序列化）"""
        return {
            'id': self.node_id,
            'text': self.text,
            'level': self.level,
            'pos': (self.pos().x(), self.pos().y()),
            'width': self.width,
            'height': self.height,
            'color': self.node_color.name(),
            'children': [child.to_dict() for child in self.child_nodes]
        }
    
    @staticmethod
    def from_dict(data, parent=None, scene=None):
        """从字典创建节点"""
        node = MindMapNode(
            text=data['text'],
            parent_node=parent,
            scene=scene,
            node_id=data['id']
        )
        
        # 设置位置
        node.setPos(QPointF(data['pos'][0], data['pos'][1]))
        
        # 设置大小
        node.width = data['width']
        node.height = data['height']
        
        # 设置颜色
        node.node_color = QColor(data['color'])
        
        # 递归创建子节点
        for child_data in data['children']:
            child_node = MindMapNode.from_dict(child_data, parent=node, scene=scene)
            node.child_nodes.append(child_node)
        
        return node


class MindMapConnection(QGraphicsItem):
    """思维导图连接线类"""
    
    def __init__(self, start_node, end_node):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        
        # 连接线属性
        self.line_width = 2
        self.line_color = QColor(150, 150, 150)
        self.line_style = Qt.SolidLine
        
        # 设置Z值（确保在节点下方）
        self.setZValue(-1)
    
    def boundingRect(self):
        """定义连接线的边界矩形"""
        start_pos = self.start_node.scenePos() + QPointF(self.start_node.width, self.start_node.height / 2)
        end_pos = self.end_node.scenePos() + QPointF(0, self.end_node.height / 2)
        
        x1, y1 = start_pos.x(), start_pos.y()
        x2, y2 = end_pos.x(), end_pos.y()
        
        return QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)).normalized().adjusted(-5, -5, 5, 5)
    
    def shape(self):
        """定义连接线的形状"""
        path = QPainterPath()
        start_pos = self.start_node.scenePos() + QPointF(self.start_node.width, self.start_node.height / 2)
        end_pos = self.end_node.scenePos() + QPointF(0, self.end_node.height / 2)
        
        # 创建曲线路径
        control_point1 = start_pos + QPointF(50, 0)
        control_point2 = end_pos - QPointF(50, 0)
        
        path.moveTo(start_pos)
        path.cubicTo(control_point1, control_point2, end_pos)
        
        # 创建笔画路径用于命中检测
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        
        return stroker.createStroke(path)
    
    def paint(self, painter, option, widget=None):
        """绘制连接线"""
        # 计算连接点
        start_pos = self.start_node.scenePos() + QPointF(self.start_node.width, self.start_node.height / 2)
        end_pos = self.end_node.scenePos() + QPointF(0, self.end_node.height / 2)
        
        # 设置画笔
        pen = QPen(self.line_color, self.line_width, self.line_style)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制贝塞尔曲线
        control_point1 = start_pos + QPointF(50, 0)
        control_point2 = end_pos - QPointF(50, 0)
        
        path = QPainterPath()
        path.moveTo(start_pos)
        path.cubicTo(control_point1, control_point2, end_pos)
        
        painter.drawPath(path)
        
        # 绘制箭头
        self.draw_arrow(painter, end_pos, path)
    
    def draw_arrow(self, painter, end_point, path):
        """在连接线末端绘制箭头"""
        # 获取曲线在末端点的切线方向
        if path.length() < 1:
            return
        
        percent = 0.99  # 在曲线末端附近取点
        point1 = path.pointAtPercent(percent - 0.01)
        point2 = path.pointAtPercent(percent)
        
        # 计算角度
        angle = math.atan2(point2.y() - point1.y(), point2.x() - point1.x())
        
        # 箭头大小
        arrow_size = 8
        
        # 计算箭头点
        arrow_p1 = QPointF(
            end_point.x() - arrow_size * math.cos(angle - math.pi / 6),
            end_point.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        arrow_p2 = QPointF(
            end_point.x() - arrow_size * math.cos(angle + math.pi / 6),
            end_point.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        
        # 绘制箭头
        painter.setBrush(self.line_color)
        polygon = QPolygonF([end_point, arrow_p1, arrow_p2])
        painter.drawPolygon(polygon)
    
    def update_path(self):
        """更新连接线路径"""
        self.prepareGeometryChange()


class MindMapScene(QGraphicsScene):
    """思维导图场景类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-500, -500, 1000, 1000)
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
        # 状态
        self.dragging = False
        self.drag_start_pos = None
        self.current_connection = None
        
        # 根节点
        self.root_node = None
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.scenePos(), QTransform())
            print(f"场景鼠标按下: item类型={type(item).__name__ if item else 'None'}")
            
            # 如果点击到空白区域（没有点击到任何项目），开始框选并清空选择
            if item is None:
                # 先退出所有编辑模式
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode) and scene_item.is_editing:
                        scene_item.finish_editing()
                
                # 取消所有节点的选中状态
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode):
                        scene_item.set_mode('normal')
                        scene_item.setSelected(False)
                
                self.dragging = True
                self.drag_start_pos = event.scenePos()
                self.setSelectionArea(QPainterPath())
                # 清空当前选择
                self.clearSelection()
                return
            
            # 查找对应的MindMapNode（处理点击到子项的情况）
            mind_map_node = None
            if isinstance(item, MindMapNode):
                mind_map_node = item
            else:
                # 如果是子项，向上查找父节点
                parent = item.parentItem()
                while parent:
                    if isinstance(parent, MindMapNode):
                        mind_map_node = parent
                        break
                    parent = parent.parentItem()
            
            # 如果点击到非节点项目（如连接线），也清空选择
            if mind_map_node is None:
                # 先退出所有编辑模式
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode) and scene_item.is_editing:
                        scene_item.finish_editing()
                
                # 取消所有节点的选中状态
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode):
                        scene_item.set_mode('normal')
                        scene_item.setSelected(False)
                
                self.clearSelection()
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode):
                        scene_item.update()
                return
            
            # 如果点击到节点，确保只有一个节点处于编辑模式
            print(f"场景: 点击到节点 {mind_map_node.text}, Ctrl键状态={event.modifiers() & Qt.ControlModifier}")
            # 退出其他节点的编辑模式
            for scene_item in self.items():
                if isinstance(scene_item, MindMapNode) and scene_item != mind_map_node and scene_item.is_editing:
                    scene_item.finish_editing()
            
            # 根据Ctrl键状态决定是否清空选择
            if not (event.modifiers() & Qt.ControlModifier):
                # 未按Ctrl键：清空选择，实现单选
                # 手动取消所有其他节点的选中状态，确保itemChange被调用
                for scene_item in self.items():
                    if isinstance(scene_item, MindMapNode) and scene_item != mind_map_node:
                        scene_item.setSelected(False)
                        scene_item.set_mode('normal')
                self.clearSelection()
                print("场景: 未按Ctrl键，清空选择")
            else:
                # 按Ctrl键：保持当前选择，实现多选
                print("场景: 按Ctrl键，保持当前选择")
        
        print("场景: 调用super().mousePressEvent")
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and self.drag_start_pos:
            # 绘制选择矩形
            rect = QRectF(self.drag_start_pos, event.scenePos()).normalized()
            path = QPainterPath()
            path.addRect(rect)
            self.setSelectionArea(path)
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self.dragging:
            self.dragging = False
            self.drag_start_pos = None
        
        super().mouseReleaseEvent(event)
    
    def add_root_node(self, text="中心主题"):
        """添加根节点"""
        if self.root_node:
            self.removeItem(self.root_node)
        
        self.root_node = MindMapNode(text, scene=self)
        self.root_node.setPos(0, 0)
        self.addItem(self.root_node)
        
        return self.root_node
    
    def save_to_file(self, filename):
        """保存思维导图到文件"""
        if not self.root_node:
            return False
        
        try:
            data = {
                'nodes': self.root_node.to_dict(),
                'scene_rect': {
                    'x': self.sceneRect().x(),
                    'y': self.sceneRect().y(),
                    'width': self.sceneRect().width(),
                    'height': self.sceneRect().height()
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存文件时出错: {e}")
            return False
    
    def load_from_file(self, filename):
        """从文件加载思维导图"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 清除场景
            self.clear()
            
            # 创建根节点
            self.root_node = MindMapNode.from_dict(data['nodes'], scene=self)
            self.addItem(self.root_node)
            
            # 添加所有连接线
            self.add_connections(self.root_node)
            
            # 设置场景矩形
            if 'scene_rect' in data:
                rect_data = data['scene_rect']
                self.setSceneRect(
                    rect_data['x'], rect_data['y'],
                    rect_data['width'], rect_data['height']
                )
            
            return True
        except Exception as e:
            print(f"加载文件时出错: {e}")
            return False
    
    def add_connections(self, node):
        """递归添加连接线"""
        for child in node.child_nodes:
            connection = MindMapConnection(node, child)
            self.addItem(connection)
            self.add_connections(child)


class MindMapView(QGraphicsView):
    """思维导图视图类"""
    
    def __init__(self, scene=None):
        super().__init__(scene if scene else MindMapScene())
        
        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 滚动条设置
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 拖拽模式 - 支持多选
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # 焦点策略 - 确保视图能够接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 启用多选 - QGraphicsView的RubberBandDrag模式默认支持多选
        
        # 缩放相关
        self.zoom_factor = 1.0
        self.zoom_step = 0.1
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建根节点
        if not self.scene().root_node:
            self.scene().add_root_node()
    
    def wheelEvent(self, event):
        """鼠标滚轮事件 - 缩放"""
        if event.modifiers() & Qt.ControlModifier:
            # 计算缩放因子
            zoom_in = event.angleDelta().y() > 0
            factor = 1.0 + self.zoom_step if zoom_in else 1.0 - self.zoom_step
            
            # 限制缩放范围
            new_zoom = self.zoom_factor * factor
            if 0.1 <= new_zoom <= 3.0:
                self.zoom_factor = new_zoom
                self.scale(factor, factor)
            
            event.accept()
        else:
            super().wheelEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MiddleButton:
            # 中键拖拽视图
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setInteractive(False)
            fake_event = QMouseEvent(
                event.type(), event.localPos(), event.screenPos(),
                Qt.LeftButton, Qt.LeftButton, event.modifiers()
            )
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setInteractive(True)
        
        super().mouseReleaseEvent(event)
    

    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        scene_pos = self.mapToScene(pos)
        item = self.scene().itemAt(scene_pos, QTransform())
        
        menu = QMenu(self)
        
        if isinstance(item, MindMapNode):
            # 节点相关操作
            add_child_action = menu.addAction("添加子节点")
            delete_action = menu.addAction("删除节点")
            edit_action = menu.addAction("编辑文本")
            menu.addSeparator()
            
            # 连接信号
            add_child_action.triggered.connect(lambda: self.add_child_node(item))
            delete_action.triggered.connect(lambda: self.delete_node(item))
            edit_action.triggered.connect(lambda: item.start_editing())
        
        # 通用操作
        add_root_action = menu.addAction("添加根节点")
        center_view_action = menu.addAction("居中视图")
        reset_zoom_action = menu.addAction("重置缩放")
        menu.addSeparator()
        export_action = menu.addAction("导出为图片")
        
        # 连接信号
        add_root_action.triggered.connect(self.add_root_node)
        center_view_action.triggered.connect(self.center_view)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        export_action.triggered.connect(self.export_image)
        
        menu.exec_(self.mapToGlobal(pos))
    
    def add_child_node(self, parent_node):
        """添加子节点"""
        child = parent_node.add_child("新节点")
        child.start_editing()
    
    def delete_node(self, node):
        """删除节点"""
        if node.parent_node:
            node.parent_node.remove_child(node)
        elif node == self.scene().root_node:
            # 如果是根节点，只清空其子节点
            for child in node.child_nodes[:]:
                node.remove_child(child)
    
    def add_root_node(self):
        """添加根节点"""
        root = self.scene().add_root_node("新中心主题")
        root.start_editing()
    
    def center_view(self):
        """居中视图"""
        if self.scene().root_node:
            self.centerOn(self.scene().root_node)
    
    def reset_zoom(self):
        """重置缩放"""
        self.zoom_factor = 1.0
        self.resetTransform()
    
    def export_image(self, filename=None):
        """导出为图片"""
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出图片", "", "PNG图片 (*.png);;JPEG图片 (*.jpg);;所有文件 (*)"
            )
            if not filename:
                return
        
        # 获取场景边界
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-50, -50, 50, 50)  # 添加边距
        
        # 创建图片
        image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
        image.fill(Qt.white)
        
        # 绘制场景到图片
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self.scene().render(painter, QRectF(image.rect()), rect)
        painter.end()
        
        # 保存图片
        image.save(filename)
        QMessageBox.information(self, "导出成功", f"图片已保存到: {filename}")


class MindMapWidget(QWidget):
    """思维导图主控件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("PyQt5思维导图")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置焦点策略 - 确保主窗口能够接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 先创建视图
        self.view = MindMapView()
        
        # 然后创建工具栏（此时self.view已经存在）
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 添加视图到布局
        main_layout.addWidget(self.view)
        
        # 状态栏
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)
        
        # 更新状态
        self.update_status()
        
        # 确保视图获得焦点
        self.view.setFocus()
        
        # 确保视图获得焦点
        self.view.setFocus()
        
        # 设置窗口为活动窗口
        self.activateWindow()
        self.raise_()
        
        # 延迟设置焦点，确保窗口完全加载
        QTimer.singleShot(100, lambda: self.view.setFocus())
        
        # 安装事件过滤器，确保捕获Tab键事件
        self.view.installEventFilter(self)
        self.installEventFilter(self)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        
        # 文件操作
        new_action = toolbar.addAction(QIcon.fromTheme("document-new"), "新建")
        open_action = toolbar.addAction(QIcon.fromTheme("document-open"), "打开")
        save_action = toolbar.addAction(QIcon.fromTheme("document-save"), "保存")
        
        toolbar.addSeparator()
        
        # 编辑操作
        add_node_action = toolbar.addAction(QIcon.fromTheme("list-add"), "添加节点")
        delete_action = toolbar.addAction(QIcon.fromTheme("list-remove"), "删除节点")
        edit_action = toolbar.addAction(QIcon.fromTheme("edit"), "编辑节点")
        
        toolbar.addSeparator()
        
        # 视图操作
        zoom_in_action = toolbar.addAction(QIcon.fromTheme("zoom-in"), "放大")
        zoom_out_action = toolbar.addAction(QIcon.fromTheme("zoom-out"), "缩小")
        reset_zoom_action = toolbar.addAction(QIcon.fromTheme("zoom-fit-best"), "重置缩放")
        center_action = toolbar.addAction(QIcon.fromTheme("go-home"), "居中视图")
        arrange_action = toolbar.addAction(QIcon.fromTheme("view-sort-ascending"), "一键整理")
        
        toolbar.addSeparator()
        
        # 导出操作
        export_action = toolbar.addAction(QIcon.fromTheme("document-export"), "导出图片")
        
        # 连接信号
        new_action.triggered.connect(self.new_mindmap)
        open_action.triggered.connect(self.open_mindmap)
        save_action.triggered.connect(self.save_mindmap)
        add_node_action.triggered.connect(self.add_node)
        delete_action.triggered.connect(self.delete_selected)
        edit_action.triggered.connect(self.edit_selected)
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_out_action.triggered.connect(self.zoom_out)
        reset_zoom_action.triggered.connect(self.view.reset_zoom)
        center_action.triggered.connect(self.view.center_view)
        arrange_action.triggered.connect(self.arrange_layout)
        export_action.triggered.connect(self.view.export_image)
        
        return toolbar
    
    def new_mindmap(self):
        """新建思维导图"""
        reply = QMessageBox.question(
            self, "确认", "是否保存当前思维导图？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
        elif reply == QMessageBox.Yes:
            if not self.save_mindmap():
                return
        
        # 清除场景
        scene = MindMapScene()
        self.view.setScene(scene)
        self.view.scene().add_root_node()
        self.update_status()
    
    def open_mindmap(self):
        """打开思维导图"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开思维导图文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if filename:
            if self.view.scene().load_from_file(filename):
                self.update_status()
                self.status_bar.showMessage(f"已打开文件: {filename}", 3000)
            else:
                QMessageBox.critical(self, "错误", "无法打开文件")
    
    def save_mindmap(self):
        """保存思维导图"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存思维导图文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            if self.view.scene().save_to_file(filename):
                self.status_bar.showMessage(f"已保存到: {filename}", 3000)
                return True
            else:
                QMessageBox.critical(self, "错误", "保存文件失败")
                return False
        
        return False
    
    def add_node(self):
        """添加节点"""
        # 获取选中的节点
        selected_items = self.view.scene().selectedItems()
        
        if selected_items:
            parent = selected_items[0]
            if isinstance(parent, MindMapNode):
                child = parent.add_child("新节点")
                child.start_editing()
        else:
            # 如果没有选中的节点，添加到根节点
            if self.view.scene().root_node:
                child = self.view.scene().root_node.add_child("新节点")
                child.start_editing()
    
    def add_child_to_selected(self):
        """为选中的节点添加子节点（Tab键功能）"""
        print("=== 开始执行add_child_to_selected方法 ===")
        
        # 获取选中的节点
        selected_items = self.view.scene().selectedItems()
        print(f"选中的项目数量: {len(selected_items)}")
        
        if selected_items:
            for i, item in enumerate(selected_items):
                print(f"选中项目 {i}: 类型={type(item).__name__}, 文本={getattr(item, 'text', 'N/A')}")
            
            parent = selected_items[0]
            if isinstance(parent, MindMapNode):
                print(f"找到父节点: {parent.text}, 层级={parent.level}")
                
                # 添加子节点
                child = parent.add_child("子节点")
                print(f"成功添加子节点: {child.text}")
                
                # 启动编辑模式
                child.start_editing()
                print(f"子节点进入编辑模式: {child.is_editing}")
                
                print(f"=== 成功为节点 '{parent.text}' 添加子节点 ===")
            else:
                print(f"错误: 选中的项目不是MindMapNode类型，而是{type(parent).__name__}")
        else:
            # 如果没有选中的节点，提示用户
            print("=== 警告: 没有选中的节点 ===")
            print("请先选中一个节点，然后按Tab键添加子节点")
    
    def delete_selected(self):
        """删除选中的节点"""
        selected_items = self.view.scene().selectedItems()
        
        for item in selected_items:
            if isinstance(item, MindMapNode):
                self.view.delete_node(item)
        
        self.update_status()
    
    def edit_selected(self):
        """编辑选中的节点"""
        selected_items = self.view.scene().selectedItems()
        
        if selected_items:
            item = selected_items[0]
            if isinstance(item, MindMapNode):
                item.start_editing()
    
    def zoom_in(self):
        """放大"""
        self.view.scale(1.1, 1.1)
        self.view.zoom_factor *= 1.1
        self.update_status()
    
    def zoom_out(self):
        """缩小"""
        self.view.scale(0.9, 0.9)
        self.view.zoom_factor *= 0.9
        self.update_status()
    
    def arrange_layout(self):
        """一键整理布局 - 使用主流思维导图布局算法"""
        print("=== 开始智能一键整理布局 ===")
        
        scene = self.view.scene()
        if not scene or not scene.root_node:
            print("警告: 没有根节点，无法整理布局")
            return
        
        # 第一步：重置缩放
        print("步骤1: 重置缩放")
        self.view.reset_zoom()
        
        # 第二步：使用新的布局算法
        print("步骤2: 执行智能分支布局")
        
        # 从根节点开始布局整个思维导图
        scene.root_node.layout_entire_mindmap_smart()
        
        # 第三步：居中视图
        print("步骤3: 居中显示整个思维导图")
        self.view.center_view()
        
        print("=== 智能一键整理完成 ===")
        
        # 更新显示
        scene.update()
    
    def calculate_mindmap_bounds(self, root_node, level_spacing, sibling_spacing):
        """计算整个思维导图的边界 - 改进版"""
        if not root_node:
            return {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}
        
        # 递归计算最大层级和每层最大子节点数量
        max_level = self.calculate_max_level(root_node, 0)
        max_children = self.calculate_max_children_per_level(root_node)
        
        # 改进的边界计算：考虑所有层级的实际分布
        max_x = max_level * level_spacing
        
        # 计算最大垂直范围：考虑所有层级的累积高度
        max_y = 0
        for level in range(1, max_level + 1):
            level_max_children = max_children.get(level, 0)
            if level_max_children > 0:
                # 每层的最大高度 = 最大子节点数 * 基础间距 / 2
                level_height = level_max_children * (60 + sibling_spacing) / 2
                max_y += level_height
        
        # 确保边界足够大以容纳所有节点
        max_y = max(max_y, 200)  # 最小边界为200
        
        return {
            'min_x': 0,
            'max_x': max_x,
            'min_y': -max_y,
            'max_y': max_y
        }
    
    def calculate_max_level(self, node, current_level):
        """计算最大层级深度"""
        if not node.child_nodes or not node.is_expanded:
            return current_level
        
        max_level = current_level
        for child in node.child_nodes:
            child_level = self.calculate_max_level(child, current_level + 1)
            max_level = max(max_level, child_level)
        
        return max_level
    
    def calculate_max_children_per_level(self, node, level=0, result=None):
        """计算每层的最大子节点数量"""
        if result is None:
            result = {}
        
        if node.child_nodes and node.is_expanded:
            # 更新当前层的子节点数量
            result[level + 1] = max(result.get(level + 1, 0), len(node.child_nodes))
            
            # 递归处理子节点
            for child in node.child_nodes:
                self.calculate_max_children_per_level(child, level + 1, result)
        
        return result
    
    def arrange_node_symmetrical(self, node, level, index, bounds, level_spacing, sibling_spacing):
        """对称布局节点及其子节点 - 改进版算法"""
        if not node:
            return
        
        # 计算节点的水平位置（基于层级）
        x = level * level_spacing
        
        # 计算节点的垂直位置（改进对称分布）
        if level == 0:
            # 根节点居中
            y = 0
        else:
            # 所有层级的子节点都基于父节点对称分布
            parent = node.parent_node
            if parent and parent.child_nodes:
                total_children = len(parent.child_nodes)
                
                # 改进的对称分布算法：每层都独立对称分布
                center_index = (total_children - 1) / 2
                
                # 计算基础间距，考虑层级深度
                base_spacing = 60 + sibling_spacing
                
                # 对于所有层级都使用相同的对称分布逻辑
                y = (index - center_index) * base_spacing
                
                # 如果是第二层及以下，需要加上父节点的垂直位置
                if level > 1:
                    parent_y = parent.scenePos().y()
                    y += parent_y
            else:
                y = index * (60 + sibling_spacing)
        
        # 设置节点位置
        node.setPos(x, y)
        print(f"对称布局节点: {node.text}, 位置: ({x:.1f}, {y:.1f}), 层级: {level}, 索引: {index}")
        
        # 递归布局子节点
        if node.child_nodes and node.is_expanded:
            for i, child in enumerate(node.child_nodes):
                self.arrange_node_symmetrical(child, level + 1, i, bounds, level_spacing, sibling_spacing)
    
    def update_status(self):
        """更新状态栏"""
        scene = self.view.scene()
        node_count = 0
        
        # 计算节点数量
        if scene.root_node:
            node_count = self.count_nodes(scene.root_node)
        
        self.status_bar.showMessage(f"节点数: {node_count} | 缩放: {self.view.zoom_factor:.1f}x")
    
    def count_nodes(self, node):
        """递归计算节点数量"""
        count = 1
        for child in node.child_nodes:
            count += self.count_nodes(child)
        return count
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 捕获键盘事件"""
        if event.type() == QEvent.KeyPress:
            # 更详细的调试信息
            key_name = self.get_key_name(event.key())
            print(f"事件过滤器捕获: 键码={event.key()}({key_name}), 修饰符={event.modifiers()}, 对象={obj}")
            
            # 测试所有按键，确认事件传递
            print(f"测试按键: {key_name} 被按下")
            
            # 直接处理所有按键，确认事件传递
            if event.key() == Qt.Key_Delete:
                print("=== 删除键被按下 ===")
                self.delete_selected()
                return True
            elif event.key() == Qt.Key_F2:
                print("=== F2键被按下 ===")
                self.edit_selected()
                return True
            elif event.key() == Qt.Key_N and event.modifiers() & Qt.ControlModifier:
                print("=== Ctrl+N被按下 ===")
                self.new_mindmap()
                return True
            elif event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
                print("=== Ctrl+O被按下 ===")
                self.open_mindmap()
                return True
            elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
                print("=== Ctrl+S被按下 ===")
                self.save_mindmap()
                return True
            elif event.key() == Qt.Key_Equal and event.modifiers() & Qt.ControlModifier:
                print("=== Ctrl+=被按下 ===")
                self.zoom_in()
                return True
            elif event.key() == Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
                print("=== Ctrl+-被按下 ===")
                self.zoom_out()
                return True
            elif event.key() == Qt.Key_Tab or event.key() == 16777217:
                print(f"=== 事件过滤器: Tab键被按下 (键码={event.key()}) ===")
                print(f"Tab键修饰符: {event.modifiers()}")
                self.add_child_to_selected()
                return True  # 阻止Tab键的默认行为
            else:
                # 对于其他按键，也打印信息但不拦截
                print(f"其他按键: {key_name} - 事件继续传递")
                return False  # 让事件继续传递
        
        return super().eventFilter(obj, event)
    
    def get_key_name(self, key_code):
        """将键码转换为可读的名称"""
        key_names = {
            Qt.Key_Delete: "Delete",
            Qt.Key_F2: "F2", 
            Qt.Key_N: "N",
            Qt.Key_O: "O",
            Qt.Key_S: "S",
            Qt.Key_Equal: "Equal",
            Qt.Key_Minus: "Minus",
            Qt.Key_Space: "Space",
            Qt.Key_A: "A",
            Qt.Key_D: "D",
            Qt.Key_F: "F",
            32: "Space",  # 空格键
            65: "A",      # A键
            68: "D",      # D键
            70: "F",      # F键
            83: "S"       # S键
        }
        return key_names.get(key_code, f"Unknown({key_code})")
    
    def keyPressEvent(self, event):
        """键盘事件"""
        # 检查是否有节点处于编辑状态
        editing_node = None
        scene = self.view.scene()
        if scene:
            for item in scene.items():
                if isinstance(item, MindMapNode) and item.is_editing:
                    editing_node = item
                    break
        
        if editing_node:
            # 如果有节点在编辑，将事件转发给文本框
            print(f"=== 键盘事件转发到编辑节点: {event.key()} ===")
            return super().keyPressEvent(event)
        
        # 更详细的调试信息
        key_name = self.get_key_name(event.key())
        print(f"=== 主窗口键盘事件: 键码={event.key()}({key_name}), 修饰符={event.modifiers()} ===")
        
        if event.key() == Qt.Key_Delete:
            print("*** 删除键被按下 - 执行删除操作 ***")
            self.delete_selected()
        elif event.key() == Qt.Key_F2:
            print("*** F2键被按下 - 执行编辑操作 ***")
            self.edit_selected()
        elif event.key() == Qt.Key_N and event.modifiers() & Qt.ControlModifier:
            print("*** Ctrl+N被按下 - 执行新建操作 ***")
            self.new_mindmap()
        elif event.key() == Qt.Key_O and event.modifiers() & Qt.ControlModifier:
            print("*** Ctrl+O被按下 - 执行打开操作 ***")
            self.open_mindmap()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            print("*** Ctrl+S被按下 - 执行保存操作 ***")
            self.save_mindmap()
        elif event.key() == Qt.Key_Equal and event.modifiers() & Qt.ControlModifier:
            print("*** Ctrl+=被按下 - 执行放大操作 ***")
            self.zoom_in()
        elif event.key() == Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
            print("*** Ctrl+-被按下 - 执行缩小操作 ***")
            self.zoom_out()
        elif event.key() == Qt.Key_Tab or event.key() == 16777217:
            print(f"*** Tab键被按下 (键码={event.key()}) - 新增子节点 ***")
            print(f"修饰符: {event.modifiers()}")
            print(f"当前是否有编辑节点: {bool(editing_node)}")
            self.add_child_to_selected()
            # 阻止Tab键的默认行为（焦点切换）
            event.accept()
        else:
            print(f"未处理的按键: {key_name}")
            super().keyPressEvent(event)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 设置调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, Qt.white)
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.black)
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.Highlight, QColor(66, 133, 244))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    
    # 创建主窗口
    widget = MindMapWidget()
    widget.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()