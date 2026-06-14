"""
终极版视频去重脚本（集成 Waifu2x-Extension-GUI）
支持: Waifu2x、DAIN、RIFE、CAIN、IFRNet、Real-CUGAN、Anime4K
"""
import os
import sys
import datetime
import random
from pathlib import Path

# 检查所有 AI 模型
MODEL_DIR = Path(__file__).parent / "models"
RIFE_MODEL_DIR = Path(__file__).parent / "RIFE_trained_model_v3.6"
CLIQ_MODEL_DIR = Path(__file__).parent / "cliqa_pretrained_models_20230419"
WAIFU2X_DIR = Path(__file__).parent / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui"

# 模型状态
AI_MODELS = {
    'waifu2x': False,
    'dain': False,
    'rife': False,
    'cain': False,
    'ifrnet': False,
    'real-cugan': False,
    'anime4k': False,
    'real-esrgan': False,
    'cliq': False,
    'esrgan': False
}

def check_all_models():
    """检查所有可用的 AI 模型"""
    print("检测 AI 模型...")
    
    # 检查 Waifu2x-Extension-GUI 包
    if WAIFU2X_DIR.exists():
        AI_MODELS['waifu2x'] = True
        print(f"  ✅ Waifu2x-Extension-GUI")
        
        # 检查内置模型
        model_checks = [
            ('dain', WAIFU2X_DIR / "dain-ncnn-vulkan"),
            ('rife', WAIFU2X_DIR / "rife-ncnn-vulkan"),
            ('cain', WAIFU2X_DIR / "cain-ncnn-vulkan"),
            ('ifrnet', WAIFU2X_DIR / "ifrnet-ncnn-vulkan"),
            ('real-cugan', WAIFU2X_DIR / "Real-CUGAN-Caffe"),
            ('anime4k', WAIFU2X_DIR / "Anime4K"),
            ('real-esrgan', WAIFU2X_DIR / "realesrgan-ncnn-vulkan"),
        ]
        
        for model_name, model_path in model_checks:
            if model_path.exists():
                AI_MODELS[model_name] = True
                print(f"    ✅ {model_name.upper()}")
    
    # 检查独立 RIFE 模型
    if RIFE_MODEL_DIR.exists():
        rife_model = RIFE_MODEL_DIR / "train_log" / "flownet.pkl"
        if rife_model.exists():
            AI_MODELS['rife'] = True
            print(f"  ✅ RIFE (独立模型)")
    
    # 检查 CLIQ 模型
    if CLIQ_MODEL_DIR.exists():
        if list(CLIQ_MODEL_DIR.rglob("*.pth")):
            AI_MODELS['cliq'] = True
            print(f"  ✅ CLIQ 质量评估")
    
    # 检查 ESRGAN 模型
    if MODEL_DIR.exists():
        if list(MODEL_DIR.glob("*.pth")):
            AI_MODELS['esrgan'] = True
            print(f"  ✅ Real-ESRGAN")

def generate_output_dir(input_dir=None):
    """生成输出目录 - 自由选择
    1. 直接回车 → 在输入视频目录同级创建"去重后视频N月N日"
    2. 输入路径 → 使用自定义路径
    """
    import datetime
    import os
    
    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"
    
    user_input = input(f"\n  输入输出目录 (回车在输入目录创建, 或输入自定义路径): ").strip()
    
    if user_input == '':
        if input_dir:
            base_dir = os.path.dirname(os.path.abspath(input_dir))
        else:
            base_dir = os.getcwd()
        folder_name = f"去重后视频{date_str}"
        output_dir = os.path.join(base_dir, folder_name)
        
        counter = 1
        while os.path.exists(output_dir):
            folder_name = f"{counter}_去重后视频{date_str}"
            output_dir = os.path.join(base_dir, folder_name)
            counter += 1
    else:
        output_dir = user_input
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"  输出目录: {output_dir}")
    return output_dir

def get_video_files(input_dir):
    """获取目录中的视频文件"""
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = []
    
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(video_extensions):
            video_files.append(os.path.join(input_dir, filename))
    
    return sorted(video_files)

def process_video_with_ai(input_path, output_dir, config):
    """使用 AI 模型处理视频
    
    AI处理流程:
    1. 帧插值 (DAIN > RIFE > CAIN > IFRNet) - 只选一个
    2. 超分辨率/画质增强 (Waifu2x / Real-CUGAN / Anime4K / Real-ESRGAN)
    3. 质量增强 (CLIQ)
    4. 标准FFmpeg去重
    """
    from progress_utils import print_step, print_ok, print_fail, Spinner
    
    # 使用GPU加速版本的视频处理器
    try:
        from video_processor_hybrid import VideoProcessor
        config['use_gpu'] = True
        print_ok("使用 GPU 加速视频处理器")
    except:
        from video_processor import VideoProcessor
        config['use_gpu'] = False
        print_ok("使用 CPU 标准处理器")
    
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    
    current_input = input_path
    temp_files = []
    
    # 统计步骤数
    total_steps = 1  # 至少FFmpeg
    use_interp = config.get('use_dain') or config.get('use_rife') or config.get('use_cain') or config.get('use_ifrnet')
    use_enhance = config.get('use_waifu2x') or config.get('use_real-cugan') or config.get('use_anime4k') or config.get('use_real-esrgan') or config.get('use_esrgan')
    if use_interp: total_steps += 1
    if use_enhance: total_steps += 1
    if config.get('use_cliq', False) and not use_enhance: total_steps += 1
    
    current_step = 0
    
    # ====== 步骤1: 帧插值 (只选一个) ======
    if use_interp:
        current_step += 1
        from waifu2x_processor import Waifu2xProcessor
        w2x = Waifu2xProcessor()
        
        temp_path = os.path.join(output_dir, f"{name}_interp_temp{ext}")
        temp_files.append(temp_path)
        
        model_name = 'DAIN'
        mode = 'dain'
        if config.get('use_dain') and w2x.models.get('dain'):
            model_name, mode = 'DAIN', 'dain'
        elif config.get('use_rife') and w2x.models.get('rife'):
            model_name, mode = 'RIFE', 'rife'
        elif config.get('use_cain') and w2x.models.get('cain'):
            model_name, mode = 'CAIN', 'cain'
        elif config.get('use_ifrnet') and w2x.models.get('ifrnet'):
            model_name, mode = 'IFRNet', 'ifrnet'
        else:
            print_fail("帧插值模型不可用")
            use_interp = False
        
        if use_interp:
            print_step(current_step, total_steps, f"{model_name} 帧插值")
            sp = Spinner(f"{model_name}生成中间帧")
            sp.start()
            success = w2x.process(current_input, temp_path, mode=mode)
            sp.stop("完成" if success else "失败")
            
            if success:
                current_input = temp_path
            else:
                print_fail("帧插值失败，使用原始视频")
    
    # ====== 步骤2: 超分辨率/画质增强 ======
    if use_enhance:
        current_step += 1
        print_step(current_step, total_steps, "画质增强")
        
        from waifu2x_processor import Waifu2xProcessor
        w2x = Waifu2xProcessor()
        
        # 收集所有可用的增强模型
        enhance_tasks = []
        if config.get('use_waifu2x'):
            enhance_tasks.append(('Waifu2x', 'waifu2x'))
        if config.get('use_real-cugan') and w2x.models.get('real-cugan'):
            enhance_tasks.append(('Real-CUGAN', 'real-cugan'))
        if config.get('use_anime4k') and w2x.models.get('anime4k'):
            enhance_tasks.append(('Anime4K', 'anime4k'))
        if config.get('use_real-esrgan') and w2x.models.get('real-esrgan'):
            enhance_tasks.append(('Real-ESRGAN', 'realesrgan'))
        if config.get('use_esrgan'):
            enhance_tasks.append(('ESRGAN独立版', 'esrgan'))
        
        if enhance_tasks:
            from progress_utils import ProgressBar
            epbar = ProgressBar(len(enhance_tasks), "画质增强")
            for ename, emode in enhance_tasks:
                temp_path = os.path.join(output_dir, f"{name}_{emode}_temp{ext}")
                temp_files.append(temp_path)
                epbar.set_description(f"{ename}")
                success = w2x.process(current_input, temp_path, mode=emode)
                if success:
                    current_input = temp_path
                epbar.update(1)
            epbar.close()
        else:
            print_fail("画质增强模型不可用")
    
    # ====== 步骤3: CLIQ 质量增强 ======
    if config.get('use_cliq', False) and not use_enhance:
        current_step += 1
        print_step(current_step, total_steps, "CLIQ 质量增强")
        
        from cliq_processor import CliqProcessor
        temp_path = os.path.join(output_dir, f"{name}_cliq_temp{ext}")
        temp_files.append(temp_path)
        
        sp = Spinner("CLIQ质量评估")
        sp.start()
        processor = CliqProcessor()
        ok = processor.process(current_input, temp_path)
        sp.stop("完成" if ok else "失败")
        
        if ok:
            current_input = temp_path
    
    # ====== 步骤4: 标准FFmpeg去重 ======
    current_step += 1
    print_step(current_step, total_steps, "FFmpeg去重处理")
    
    output_path = os.path.join(output_dir, f"{name}_AI去重{ext}")
    sp = Spinner("FFmpeg分段+滤镜+元数据")
    sp.start()
    processor = VideoProcessor(current_input, output_path, config)
    success = processor.run()
    sp.stop("完成" if success else "失败")
    
    # 清理临时文件
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
    
    return success

def batch_process(input_dir, config):
    """批量处理视频"""
    video_files = get_video_files(input_dir)
    
    if not video_files:
        print("未找到视频文件")
        return
    
    output_dir = generate_output_dir(input_dir)
    print(f"发现 {len(video_files)} 个视频文件")
    
    success_count = 0
    for i, video_path in enumerate(video_files, 1):
        print(f"\n处理 [{i}/{len(video_files)}]: {os.path.basename(video_path)}")
        
        if process_video_with_ai(video_path, output_dir, config):
            success_count += 1
    
    print(f"\n=== 处理完成 ===")
    print(f"成功: {success_count}/{len(video_files)}")

def show_model_info():
    """显示可用模型信息"""
    print("\n📦 可用的 AI 模型:")
    print("-" * 60)
    
    model_descriptions = {
        'waifu2x': 'Waifu2x 超分辨率',
        'dain': 'DAIN 帧插值（最强）',
        'rife': 'RIFE 帧插值（强）',
        'cain': 'CAIN 帧插值',
        'ifrnet': 'IFRNet 帧插值',
        'real-cugan': 'Real-CUGAN 动漫超分',
        'anime4k': 'Anime4K 画质增强',
        'real-esrgan': 'Real-ESRGAN 超分(Waifu2x)',
        'cliq': 'CLIQ 质量评估',
        'esrgan': 'Real-ESRGAN 超分辨率',
    }
    
    for model, available in AI_MODELS.items():
        status = "✅" if available else "❌"
        print(f"  {status} {model_descriptions.get(model, model)}")
    
    print("-" * 60)

def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='终极版视频去重脚本')
    parser.add_argument('input_dir', nargs='?', help='视频目录')
    parser.add_argument('--mode', choices=['standard', 'ai', 'custom'], default='ai',
                        help='处理模式: standard(标准), ai(AI增强), custom(自定义)')
    return parser.parse_known_args()[0]

def main():
    """主程序"""
    print("=" * 60)
    print("终极版视频去重脚本")
    print("集成 Waifu2x-Extension-GUI")
    print("=" * 60)
    
    # 检查模型
    check_all_models()
    
    # 显示模型信息
    show_model_info()
    
    print("\n自动进入批量处理模式...")
    
    # 解析参数
    args = parse_args()
    
    # 获取输入目录
    if args.input_dir:
        input_dir = args.input_dir
        print(f"使用命令行参数作为目录: {input_dir}")
    elif len(sys.argv) > 1:
        input_dir = sys.argv[1]
        print(f"使用命令行参数作为目录: {input_dir}")
    else:
        input_dir = input("请输入视频目录路径: ").strip()
    
    if not os.path.isdir(input_dir):
        print("无效的目录路径")
        return
    
    # 检查是否通过命令行指定了模式
    mode_specified = args.mode != 'ai' or '--mode' in sys.argv
    
    config = {}
    
    if not mode_specified:
        # 交互式模式选择（直接运行时）
        print("\n🎯 选择处理模式:")
        print("  1. 标准模式 (快速稳定)")
        print("  2. AI增强模式 (最强去重)")
        print("  3. 自定义模式")
        
        choice = input("请选择模式 (1/2/3): ").strip()
    else:
        # 命令行模式（从run.py调用时）
        choice = {'standard': '1', 'ai': '2', 'custom': '3'}.get(args.mode, '2')
    
    if choice == '1':
        print("将使用标准 FFmpeg 处理模式")
    
    elif choice == '2':
        print("\n启用所有可用的 AI 增强:")
        
        if AI_MODELS['dain']:
            config['use_dain'] = True
            print("  ✓ DAIN 帧插值")
        elif AI_MODELS['rife']:
            config['use_rife'] = True
            print("  ✓ RIFE 帧插值")
        
        if AI_MODELS['waifu2x']:
            config['use_waifu2x'] = True
            print("  ✓ Waifu2x 画质增强")
        
        if AI_MODELS['cliq']:
            config['use_cliq'] = True
            print("  ✓ CLIQ 质量增强")
    
    elif choice == '3':
        if mode_specified:
            # 如果通过命令行指定自定义模式，启用所有AI
            print("\n自定义模式 - 启用所有可用 AI:")
            if AI_MODELS['dain']:
                config['use_dain'] = True
                print("  ✓ DAIN 帧插值")
            elif AI_MODELS['rife']:
                config['use_rife'] = True
                print("  ✓ RIFE 帧插值")
            if AI_MODELS['waifu2x']:
                config['use_waifu2x'] = True
                print("  ✓ Waifu2x 画质增强")
            if AI_MODELS['cliq']:
                config['use_cliq'] = True
                print("  ✓ CLIQ 质量增强")
        else:
            # 交互式自定义选择
            print("\n自定义处理选项:")
            
            if AI_MODELS['dain']:
                choice = input("  [DAIN] 是否启用帧插值? (y/n): ").strip().lower()
                config['use_dain'] = choice == 'y'
            
            if AI_MODELS['rife'] and not config.get('use_dain'):
                choice = input("  [RIFE] 是否启用帧插值? (y/n): ").strip().lower()
                config['use_rife'] = choice == 'y'
            
            if AI_MODELS['waifu2x']:
                choice = input("  [Waifu2x] 是否启用画质增强? (y/n): ").strip().lower()
                config['use_waifu2x'] = choice == 'y'
            
            if AI_MODELS['cliq']:
                choice = input("  [CLIQ] 是否启用质量增强? (y/n): ").strip().lower()
                config['use_cliq'] = choice == 'y'
    
    else:
        print("无效选择，使用标准模式")
    
    # 显示配置摘要
    print("\n📋 处理配置:")
    if config:
        for k, v in config.items():
            if v:
                print(f"  ✓ {k.replace('use_', '').upper()}")
    else:
        print("  标准 FFmpeg 处理")
    
    batch_process(input_dir, config)

if __name__ == "__main__":
    main()
