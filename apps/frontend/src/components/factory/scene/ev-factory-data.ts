// Procedural EV factory geometry imported from the EV-3D-map prototype.
export interface ZoneInfo {
  id: string;
  name: string;
  nameEn: string;
  code: string;
  dimensions: {
    length: number; // in meters (X axis)
    width: number;  // in meters (Z axis)
    height: number; // in meters (Y axis)
    xStart: number;
    xEnd: number;
    zStart: number;
    zEnd: number;
  };
  floorColor: string;
  wallColor: string;
  description: string;
  features: string[];
  subZones?: {
    id: string;
    name: string;
    description: string;
    color: string;
    bounds: { x: number; z: number; w: number; d: number };
  }[];
}

export interface MachineEquipment {
  id: string;
  zoneId: string;
  subZoneId?: string;
  name: string;
  type: 'rack' | 'robot_welder' | 'die_cast' | 'assembly_station' | 'conveyor' | 'amr' | 'qc_station' | 'loading_dock' | 'inspection_station' | 'sliding_door' | 'ev_storage';
  position: [number, number, number]; // [x, y, z] in meters
  rotation?: [number, number, number]; // [rx, ry, rz] in radians
  dimensions: [number, number, number]; // [width, height, depth]
  status: 'Operational' | 'Active' | 'Idle' | 'Maintenance' | 'Inspecting';
  powerRating?: string;
  cycleTime?: string;
  capacity?: string;
  specs: {
    label: string;
    value: string;
  }[];
  description: string;
}

export interface AMRRouteWaypoint {
  x: number;
  z: number;
  name?: string;
  action?: 'wait' | 'turn' | 'pick' | 'drop' | 'charge';
  delayMs?: number;
}

export const FACTORY_ZONES: ZoneInfo[] = [
  {
    id: 'zone-a',
    code: 'KHU VỰC A',
    name: 'Kho lưu trữ & Nhận hàng',
    nameEn: 'Warehouse & Receiving Area',
    dimensions: {
      length: 40, // 40m
      width: 30,  // 30m
      height: 8,  // 8m
      xStart: 0,
      xEnd: 40,
      zStart: -15,
      zEnd: 15,
    },
    floorColor: '#4b5563', // Gray epoxy
    wallColor: '#f3f4f6', // Clean industrial white
    description: 'Khu tiếp nhận nguyên vật liệu thô, khung gầm EV, cell pin, linh kiện điện tử và lưu trữ trên kệ cao tầng 4 dãy dọc với hệ thống quản lý kho WMS.',
    features: [
      'Cổng nhận hàng (Loading Dock) với 02 bến xếp dỡ thủy lực',
      '04 hàng kệ chứa linh kiện cao tầng (Pallet Racking) màu xanh dương',
      'Lối đi giữa các kệ rộng 3.0m tiêu chuẩn xe tự hành AMR',
      'Khu vực kiểm kê (Inspection Area) QA/QC đầu vào',
      'Điểm sạc nhanh và bãi đỗ xe tự hành AMR Warehouse Fleet'
    ],
    subZones: [
      {
        id: 'zone-a-dock',
        name: 'Bến Nhận Hàng (Loading Dock 1 & 2)',
        description: '2 bến tiếp nhận container chở linh kiện pin, động cơ điện và tôn dập',
        color: '#3b82f6',
        bounds: { x: 3, z: 0, w: 6, d: 24 }
      },
      {
        id: 'zone-a-inspection',
        name: 'Khu Vực Kiểm Kê (Receiving Inspection)',
        description: 'Bàn kiểm tra chất lượng linh kiện đầu vào, máy quét mã vạch 3D',
        color: '#eab308',
        bounds: { x: 12, z: 8, w: 8, d: 10 }
      },
      {
        id: 'zone-a-racks',
        name: 'Kho Kệ Cao Tầng (High-bay Racking Rows 1-4)',
        description: '4 dãy kệ pallet xanh dương tải trọng 2.5 tấn/ngăn, chiều cao 6.5m',
        color: '#2563eb',
        bounds: { x: 26, z: 0, w: 20, d: 24 }
      }
    ]
  },
  {
    id: 'zone-b',
    code: 'KHU VỰC B',
    name: 'Khu vực sản xuất chính',
    nameEn: 'Production Area (Welding, Casting, Assembly)',
    dimensions: {
      length: 50, // 50m
      width: 40,  // 40m
      height: 10, // 10m high ceiling
      xStart: 40,
      xEnd: 90,
      zStart: -20,
      zEnd: 20,
    },
    floorColor: '#374151', // Dark gray industrial floor
    wallColor: '#f9fafb', // Bright white with yellow safety stripes
    description: 'Trung tâm gia công chế tạo xe điện: Đúc nhôm áp lực cao (Giga-casting), trạm hàn robot 6 bậc tự do và dây chuyền lắp ráp chữ U 5 công đoạn.',
    features: [
      'Phân khu đúc (Die-casting): Máy ép đúc Giga-press 6000T + bể làm mát chi tiết',
      'Phân khu hàn (Welding): 02 trạm robot hàn 6 trục công nghiệp + băng chuyền trung chuyển',
      'Phân khu lắp ráp cuối (Final Assembly): Dây chuyền chữ U 05 trạm lắp ráp xe điện',
      'Lối đi chính trung tâm rộng 4.0m cho AMR chạy hai chiều vạch sơn vàng phản quang',
      'Điểm giao nhận linh kiện (Material Transfer Points) có viền sọc cảnh báo an toàn'
    ],
    subZones: [
      {
        id: 'zone-b-casting',
        name: 'Phân Khu Đúc Áp Lực (Die-casting & Cooling)',
        description: 'Máy đúc Giga-casting nhôm đúc nguyên khối khung gầm + khu làm nguội',
        color: '#f97316',
        bounds: { x: 52, z: -11, w: 18, d: 14 }
      },
      {
        id: 'zone-b-welding',
        name: 'Phân Khu Hàn Robot (Automated Robotic Welding)',
        description: '2 trạm robot hàn KUKA/ABB tốc độ cao, buồng rèm chắn hồ quang quang học',
        color: '#ef4444',
        bounds: { x: 74, z: -11, w: 22, d: 14 }
      },
      {
        id: 'zone-b-assembly',
        name: 'Phân Khu Lắp Ráp Chữ U (Final Assembly U-Line)',
        description: 'Dây chuyền chữ U khép kín 5 trạm: Pin -> Treo -> Nội thất -> Thân vỏ -> Bánh xe',
        color: '#10b981',
        bounds: { x: 65, z: 10, w: 40, d: 16 }
      }
    ]
  },
  {
    id: 'zone-c',
    code: 'KHU VỰC C',
    name: 'Thành phẩm & Xuất hàng',
    nameEn: 'Finished Goods & Shipping',
    dimensions: {
      length: 30, // 30m
      width: 30,  // 30m
      height: 8,  // 8m
      xStart: 90,
      xEnd: 120,
      zStart: -15,
      zEnd: 15,
    },
    floorColor: '#6b7280', // Light gray cleanroom finish
    wallColor: '#f3f4f6', // Clean industrial white
    description: 'Khu vực kiểm định chất lượng xuất xưởng (Final QC), chạy thử nghiệm dynamometer, bãi đỗ xe EV chờ giao và 02 bến xuất hàng lên xe lồng chuyên dụng.',
    features: [
      'Khu vực kiểm tra chất lượng cuối (Final QC) 02 trạm kiểm tra góc đặt bánh, phanh & ADAS',
      'Khu vực kiểm tra vạch đỏ Red-line Safety Zone chống rung động sai số',
      'Bãi lưu trữ tạm và bảo vệ phủ màng xe điện thành phẩm',
      'Cổng xuất hàng (Shipping Docks) đối diện cổng nhận hàng với 02 bến vận tải'
    ],
    subZones: [
      {
        id: 'zone-c-qc',
        name: 'Trạm Kiểm Định Xuất Xưởng (Final QC Test)',
        description: 'Trạm 1: Cân chỉnh đèn & radar ADAS; Trạm 2: Băng thử phanh & tốc độ Dynamometer',
        color: '#dc2626',
        bounds: { x: 97, z: 0, w: 10, d: 20 }
      },
      {
        id: 'zone-c-storage',
        name: 'Bãi Xe Thành Phẩm (EV Staging & Buffer)',
        description: 'Vị trí đỗ xe điện hoàn thiện sẵn sàng dán tem kiểm định và nạp pin 80%',
        color: '#06b6d4',
        bounds: { x: 108, z: -6, w: 12, d: 14 }
      },
      {
        id: 'zone-c-shipping',
        name: 'Cổng Xuất Hàng (Shipping Bays 1 & 2)',
        description: '2 bến xuất hàng xe vận chuyển chuyên dụng 2 tầng đi đại lý',
        color: '#8b5cf6',
        bounds: { x: 116, z: 0, w: 6, d: 22 }
      }
    ]
  }
];

export const FACTORY_EQUIPMENT_DATA: MachineEquipment[] = [
  // Zone A Equipment
  {
    id: 'dock-a-1',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-dock',
    name: 'Bến Nhập Hàng #01 (Dock Leveler 1)',
    type: 'loading_dock',
    position: [1.5, 1.2, -6],
    dimensions: [3, 2.5, 4],
    status: 'Active',
    powerRating: '7.5 kW Hydraulic',
    capacity: '15,000 kg Dynamic Load',
    specs: [
      { label: 'Kích thước bến', value: '3.0m x 4.0m' },
      { label: 'Loại sàn nâng', value: 'Hydraulic Pit Leveler' },
      { label: 'Cảm biến an toàn', value: 'Wheel Chock Interlock' },
      { label: 'Loại hàng nhập', value: 'Khối pin LFP & Khung gầm nhôm' }
    ],
    description: 'Bến nhập hàng tiếp nhận xe container 40ft chở linh kiện module pin từ cảng về nhà máy.'
  },
  {
    id: 'dock-a-2',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-dock',
    name: 'Bến Nhập Hàng #02 (Dock Leveler 2)',
    type: 'loading_dock',
    position: [1.5, 1.2, 6],
    dimensions: [3, 2.5, 4],
    status: 'Operational',
    powerRating: '7.5 kW Hydraulic',
    capacity: '15,000 kg Dynamic Load',
    specs: [
      { label: 'Kích thước bến', value: '3.0m x 4.0m' },
      { label: 'Loại sàn nâng', value: 'Hydraulic Pit Leveler' },
      { label: 'Loại hàng nhập', value: 'Động cơ điện & Chip điều khiển ECU' }
    ],
    description: 'Bến nhập hàng số 2 chuyên tiếp nhận hệ thống truyền động điện (e-Axle) và biến tần SiC.'
  },
  {
    id: 'inspect-a',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-inspection',
    name: 'Trạm Kiểm Kê Vật Tư Đầu Vào (Receiving Inspection Station)',
    type: 'inspection_station',
    position: [12, 1, 8],
    dimensions: [5, 2, 4],
    status: 'Inspecting',
    cycleTime: '45 giây / pallet',
    specs: [
      { label: 'Hệ thống quét', value: '3D Optical LiDAR & RFID WMS' },
      { label: 'Độ chính xác', value: '±0.1 mm kích thước hình học' },
      { label: 'Trọng lượng tối đa', value: '2,000 kg / pallet' }
    ],
    description: 'Khu vực kiểm tra dung sai kích thước và quét mã QR xác thực nguồn gốc cell pin trước khi nhập kệ tự động.'
  },
  {
    id: 'rack-a-row1',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-racks',
    name: 'Dãy Kệ K1 - Module Pin & Điện Áp Cao (Battery Pack Racking)',
    type: 'rack',
    position: [20, 3.25, -9],
    dimensions: [16, 6.5, 2.2],
    status: 'Operational',
    capacity: '128 Pallets (320 tấn)',
    specs: [
      { label: 'Số tầng kệ', value: '4 tầng (Heavy-duty)' },
      { label: 'Chiều rộng kệ', value: '16.0m x 2.2m x 6.5m' },
      { label: 'Hệ thống chữa cháy', value: 'Đầu phun FM200 chuyên dụng cho pin Li-ion' },
      { label: 'Màu sắc kết cấu', value: 'Khung xanh dương RAL 5015, Thanh đỡ cam RAL 2004' }
    ],
    description: 'Dãy kệ cao 6.5m chuyên chứa các module pin 800V được đóng gói chống tĩnh điện và cảm biến nhiệt độ tự động.'
  },
  {
    id: 'rack-a-row2',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-racks',
    name: 'Dãy Kệ K2 - Khung Động Cơ & Hộp Số (Motor & Transmission Racking)',
    type: 'rack',
    position: [20, 3.25, -3],
    dimensions: [16, 6.5, 2.2],
    status: 'Operational',
    capacity: '128 Pallets (280 tấn)',
    specs: [
      { label: 'Số tầng kệ', value: '4 tầng (Heavy-duty)' },
      { label: 'Khoảng cách lối đi AMR', value: '3.0m thông thoáng' },
      { label: 'Tải trọng mỗi khoang', value: '2,500 kg' }
    ],
    description: 'Dãy kệ số 2 lưu trữ motor nam châm vĩnh cửu PMSM và bộ giảm tốc hành tinh.'
  },
  {
    id: 'rack-a-row3',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-racks',
    name: 'Dãy Kệ K3 - Linh Kiện Khung Gầm & Treo (Chassis Components)',
    type: 'rack',
    position: [20, 3.25, 3],
    dimensions: [16, 6.5, 2.2],
    status: 'Operational',
    capacity: '128 Pallets (250 tấn)',
    specs: [
      { label: 'Số tầng kệ', value: '4 tầng' },
      { label: 'Chủng loại lưu kho', value: 'Đòn treo chữ A, phanh đĩa đục lỗ, giảm chấn khí nén' }
    ],
    description: 'Dãy kệ số 3 chứa phụ tùng hệ thống treo trước/sau và cơ cấu lái trợ lực điện EPS.'
  },
  {
    id: 'rack-a-row4',
    zoneId: 'zone-a',
    subZoneId: 'zone-a-racks',
    name: 'Dãy Kệ K4 - Điện Tử & Nội Thất (Infotainment & Wire Harness)',
    type: 'rack',
    position: [20, 3.25, 9],
    dimensions: [16, 6.5, 2.2],
    status: 'Operational',
    capacity: '128 Pallets (180 tấn)',
    specs: [
      { label: 'Số tầng kệ', value: '4 tầng' },
      { label: 'Kiểm soát môi trường', value: 'Độ ẩm < 50%, chống phóng tĩnh điện ESD' }
    ],
    description: 'Dãy kệ số 4 chứa cụm màn hình trung tâm OLED, cụm dây điện cao áp và chip bán dẫn.'
  },

  // Zone B Equipment
  {
    id: 'casting-press-1',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-casting',
    name: 'Máy Đúc Áp Lực Giga-Press 6000T (High-Pressure Die Casting)',
    type: 'die_cast',
    position: [50, 3.5, -11],
    dimensions: [12, 7, 6],
    status: 'Active',
    powerRating: '450 kW Hydraulic & Electric Servo',
    cycleTime: '90 giây / đúc nguyên khối',
    capacity: 'Lực kẹp khuôn 60,000 kN',
    specs: [
      { label: 'Kích thước máy', value: '12m (D) x 6m (R) x 7m (C)' },
      { label: 'Vật liệu đúc', value: 'Hợp kim nhôm nguyên khối Al-Si chuyên dụng EV' },
      { label: 'Sản phẩm đầu ra', value: 'Khung gầm sau xe điện đúc liền khối (Rear Underbody)' },
      { label: 'Bể tôi & làm mát', value: 'Bể nhúng làm nguội tuần hoàn nước lạnh 25°C' }
    ],
    description: 'Siêu máy đúc áp lực cao thay thế 70 mối hàn dập truyền thống bằng 1 chi tiết nhôm nguyên khối siêu nhẹ và cứng vững.'
  },
  {
    id: 'welding-robot-1',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-welding',
    name: 'Robot Hàn Tự Động #01 (6-Axis Laser/Spot Welder Alpha)',
    type: 'robot_welder',
    position: [70, 2, -13],
    dimensions: [3, 4, 3],
    status: 'Active',
    cycleTime: '35 giây / mối hàn cấu trúc',
    powerRating: '45 kW Fiber Laser',
    specs: [
      { label: 'Loại robot', value: 'Cánh tay robot 6 bậc tự do bán kính 3.1m' },
      { label: 'Công nghệ hàn', value: 'Hàn Laser sợi quang + Hàn bấm điện trở Spot Welding' },
      { label: 'Vật liệu gia công', value: 'Thép siêu cường Martensite 1500 MPa & Nhôm 6000-series' },
      { label: 'An toàn quang học', value: 'Màn chắn rèm quang học lọc bức xạ tia hồ quang' }
    ],
    description: 'Trạm robot hàn điểm chính xác cao kết nối khung phụ trước và vòm bánh xe điện.'
  },
  {
    id: 'welding-robot-2',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-welding',
    name: 'Robot Hàn Tự Động #02 (6-Axis Laser/Spot Welder Beta)',
    type: 'robot_welder',
    position: [78, 2, -13],
    dimensions: [3, 4, 3],
    status: 'Active',
    cycleTime: '35 giây / mối hàn cấu trúc',
    powerRating: '45 kW Fiber Laser',
    specs: [
      { label: 'Loại robot', value: 'Cánh tay robot 6 trục độ lặp lại ±0.03mm' },
      { label: 'Băng chuyền liên kết', value: 'Băng chuyền con lăn chịu tải 1.2 tấn kết nối 2 trạm' }
    ],
    description: 'Trạm robot hàn số 2 hoàn thiện gia cố trụ B, thanh giằng chống va đập cửa xe.'
  },
  {
    id: 'assembly-st1',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-assembly',
    name: 'Trạm Lắp Ráp 1 - Kết Hợp Pin & Khung Gầm (Battery Marriage)',
    type: 'assembly_station',
    position: [52, 1.8, 14],
    dimensions: [6, 3.5, 4],
    status: 'Active',
    cycleTime: '120 giây / xe',
    specs: [
      { label: 'Công đoạn', value: 'Nâng và siết 32 bu-lông tự động khối pin 800V vào gầm' },
      { label: 'Lực siết mô-men', value: '185 Nm có giám sát góc quay kỹ thuật số' }
    ],
    description: 'Trạm kết hôn cơ khí: Khối pin xe điện được thang nâng tự động gắn chính xác tuyệt đối vào khung thân xe.'
  },
  {
    id: 'assembly-st2',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-assembly',
    name: 'Trạm Lắp Ráp 2 - Hệ Thống Treo & Cụm Phanh (Suspension & Axles)',
    type: 'assembly_station',
    position: [62, 1.8, 14],
    dimensions: [6, 3.5, 4],
    status: 'Active',
    cycleTime: '110 giây / xe',
    specs: [
      { label: 'Công đoạn', value: 'Lắp hệ thống treo độc lập đa liên kết và cùm phanh tái sinh' },
      { label: 'Dụng cụ', value: 'Súng siết lực không dây IoT Atlas Copco' }
    ],
    description: 'Gắn cụm trục dẫn động điện e-Axle cầu trước/sau và giảm chấn thích ứng.'
  },
  {
    id: 'assembly-st3',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-assembly',
    name: 'Trạm Lắp Ráp 3 - Nội Thất & Taplo Cockpit (Interior Integration)',
    type: 'assembly_station',
    position: [74, 1.8, 14],
    dimensions: [6, 3.5, 4],
    status: 'Active',
    cycleTime: '130 giây / xe',
    specs: [
      { label: 'Công đoạn', value: 'Cẩu robot phụ trợ đưa nguyên cụm Taplo, HUD và ghế công thái học vào khoang' }
    ],
    description: 'Lắp ráp bảng điều khiển kỹ thuật số, vô lăng trợ lực và dàn âm thanh vòm.'
  },
  {
    id: 'assembly-st4',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-assembly',
    name: 'Trạm Lắp Ráp 4 - Cánh Cửa & Kính Kép (Doors & Glazing)',
    type: 'assembly_station',
    position: [82, 1.8, 8],
    dimensions: [6, 3.5, 4],
    status: 'Active',
    cycleTime: '100 giây / xe',
    specs: [
      { label: 'Công đoạn', value: 'Robot tra keo Polyurethane tự động và ép kính nóc Panoramic' }
    ],
    description: 'Gắn 4 cánh cửa liền ron cách âm và kính chắn gió chống tia UV.'
  },
  {
    id: 'assembly-st5',
    zoneId: 'zone-b',
    subZoneId: 'zone-b-assembly',
    name: 'Trạm Lắp Ráp 5 - Lắp Bánh Xe & Kích Hoạt Điện (Wheels & Power-On)',
    type: 'assembly_station',
    position: [70, 1.8, 4],
    dimensions: [6, 3.5, 4],
    status: 'Active',
    cycleTime: '90 giây / xe',
    specs: [
      { label: 'Công đoạn', value: 'Siết đồng thời 5 đai ốc bánh xe mỗi bên & nạp firmware xe' },
      { label: 'Kết quả', value: 'Xe điện tự lăn bánh bằng nguồn pin nội bộ ra phân khu C' }
    ],
    description: 'Lắp 4 lốp xe điện khí động học và khởi động hệ điều hành xe điện lần đầu tiên.'
  },

  // Zone C Equipment
  {
    id: 'qc-station-1',
    zoneId: 'zone-c',
    subZoneId: 'zone-c-qc',
    name: 'Trạm QC #01 - Cân Chỉnh Góc Đặt Bánh & Cảm Biến ADAS (Wheel Alignment)',
    type: 'qc_station',
    position: [98, 1.5, -5],
    dimensions: [6, 3, 4.5],
    status: 'Operational',
    cycleTime: '120 giây / xe',
    specs: [
      { label: 'Công nghệ', value: '3D Camera Laser Wheel Alignment & ADAS Calibration Radar' },
      { label: 'Độ chính xác góc camber/toe', value: '±0.01 độ' },
      { label: 'Đánh dấu sàn', value: 'Khu vực vạch kẻ đỏ an toàn Red-line Safe Zone' }
    ],
    description: 'Kiểm tra và chuẩn hóa độ chụm bánh xe, góc lái trung tâm và hiệu chuẩn camera tự hành ADAS Level 2+.'
  },
  {
    id: 'qc-station-2',
    zoneId: 'zone-c',
    subZoneId: 'zone-c-qc',
    name: 'Trạm QC #02 - Thử Nghiệm Con Lăn & Phanh Khẩn Cấp (Dynamometer Test)',
    type: 'qc_station',
    position: [98, 1.5, 5],
    dimensions: [6, 3, 4.5],
    status: 'Active',
    cycleTime: '150 giây / xe',
    specs: [
      { label: 'Tốc độ thử nghiệm', value: 'Lên tới 140 km/h trên con lăn' },
      { label: 'Kiểm tra', value: 'Lực phanh ABS, phản hồi mô-men xoắn motor, độ ồn NVH' }
    ],
    description: 'Mô phỏng chạy đường trường trên dàn dyno 4 bánh tải trọng cao, kiểm tra khả năng thu hồi năng lượng phanh.'
  },
  {
    id: 'shipping-dock-1',
    zoneId: 'zone-c',
    subZoneId: 'zone-c-shipping',
    name: 'Cổng Xuất Xe Thành Phẩm #01 (Shipping Bay Outbound 1)',
    type: 'loading_dock',
    position: [118.5, 1.2, -6],
    dimensions: [3, 2.5, 4],
    status: 'Operational',
    capacity: 'Xe chuyên dụng chở 8 EV / chuyến',
    specs: [
      { label: 'Loại cổng', value: 'Cầu nâng dốc xuất hàng trực tiếp lên xe lồng vận chuyển' },
      { label: 'Tiêu chuẩn giao hàng', value: 'SOC Pin 80%, dán màng bảo vệ sơn nano' }
    ],
    description: 'Cổng xuất thành phẩm phía đối diện cổng nhận hàng A, đảm bảo luồng sản xuất một chiều (One-Piece Flow).'
  },
  {
    id: 'shipping-dock-2',
    zoneId: 'zone-c',
    subZoneId: 'zone-c-shipping',
    name: 'Cổng Xuất Xe Thành Phẩm #02 (Shipping Bay Outbound 2)',
    type: 'loading_dock',
    position: [118.5, 1.2, 6],
    dimensions: [3, 2.5, 4],
    status: 'Active',
    capacity: 'Xe chuyên dụng chở 8 EV / chuyến',
    specs: [
      { label: 'Loại cổng', value: 'Cầu nâng dốc xuất hàng trực tiếp lên xe lồng vận chuyển' }
    ],
    description: 'Cổng xuất thành phẩm số 2 phục vụ các tuyến vận chuyển đại lý nội địa & xuất khẩu.'
  }
];

export const AMR_FLEET_DATA = [
  {
    id: 'amr-01',
    name: 'AMR-Transporter 01 (Linh Kiện Pin)',
    type: 'Heavy Load AMR',
    color: '#f59e0b',
    payload: 'Module Pin 800V',
    currentSpeed: '1.2 m/s',
    battery: 94,
    status: 'Giao hàng Zone A ➔ Zone B',
    path: [
      { x: 20, z: -9 }, // Rack 1
      { x: 32, z: -9 },
      { x: 32, z: 0 },
      { x: 40, z: 0 }, // Door 1
      { x: 52, z: 0 },
      { x: 52, z: 10 }, // Assembly 1
      { x: 52, z: 14 },
      { x: 52, z: 10 },
      { x: 52, z: 0 },
      { x: 40, z: 0 },
      { x: 20, z: 0 },
      { x: 20, z: -9 }
    ]
  },
  {
    id: 'amr-02',
    name: 'AMR-Transporter 02 (Khung Gầm & Đúc)',
    type: 'High-payload Pallet AMR',
    color: '#06b6d4',
    payload: 'Khung Đúc Sau Giga-Cast',
    currentSpeed: '1.0 m/s',
    battery: 88,
    status: 'Vận chuyển Phân khu Đúc ➔ Hàn',
    path: [
      { x: 52, z: -11 }, // Casting area
      { x: 52, z: -4 },
      { x: 65, z: -4 },
      { x: 74, z: -4 },
      { x: 74, z: -10 }, // Welding area
      { x: 74, z: -4 },
      { x: 65, z: -4 },
      { x: 52, z: -4 },
      { x: 52, z: -11 }
    ]
  },
  {
    id: 'amr-03',
    name: 'AMR-Transporter 03 (Thành Phẩm & QC)',
    type: 'Tugger AMR Logistics',
    color: '#10b981',
    payload: 'Bộ Linh Kiện QC & Sạc',
    currentSpeed: '1.4 m/s',
    battery: 76,
    status: 'Tuần tra & Tiếp liệu Zone B ➔ Zone C',
    path: [
      { x: 70, z: 4 }, // End of assembly
      { x: 86, z: 4 },
      { x: 86, z: 0 },
      { x: 90, z: 0 }, // Door 2
      { x: 98, z: 0 },
      { x: 98, z: -5 }, // QC 1
      { x: 108, z: -5 }, // Storage
      { x: 108, z: 0 },
      { x: 90, z: 0 },
      { x: 70, z: 0 },
      { x: 70, z: 4 }
    ]
  }
];
