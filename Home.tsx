import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Target, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TradeData {
  side: string;
  entry: number;
  exit: number;
  pnl: number;
  reason: string;
  time: string;
}

interface MetricsData {
  totalTrades: number;
  totalProfit: number;
  winRate: number;
  finalBalance: number;
  trades: TradeData[];
}

export default function Home() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState<any[]>([]);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);

  useEffect(() => {
    // Simulate fetching data from the simulator
    const fetchData = async () => {
      try {
        // Mock data - in real scenario this would come from your backend
        const mockData: MetricsData = {
          totalTrades: 53,
          totalProfit: -2028.02,
          winRate: 41.51,
          finalBalance: -1028.02,
          trades: Array.from({ length: 53 }, (_, i) => ({
            side: i % 2 === 0 ? "BUY" : "SELL",
            entry: 1.0850 + (Math.random() - 0.5) * 0.01,
            exit: 1.0850 + (Math.random() - 0.5) * 0.01,
            pnl: (Math.random() - 0.5) * 100,
            reason: Math.random() > 0.7 ? "SL" : "TP",
            time: new Date(Date.now() - i * 3600000).toISOString(),
          })),
        };

        setMetrics(mockData);

        // Generate equity curve
        let balance = 1000;
        const equityData: any[] = [];
        mockData.trades.forEach((trade, idx) => {
          balance += trade.pnl;
          equityData.push({
            trade: idx + 1,
            equity: balance,
            profit: balance - 1000,
          });
        });
        setEquityCurve(equityData);

        // Generate win/loss chart
        const wins = mockData.trades.filter((t) => t.pnl > 0).length;
        const losses = mockData.trades.filter((t) => t.pnl <= 0).length;
        const chartDataTemp: any[] = [
          { name: "Wins", value: wins, fill: "#10b981" },
          { name: "Losses", value: losses, fill: "#ef4444" },
        ];
        setChartData(chartDataTemp);

        setLoading(false);
      } catch (error) {
        console.error("Error fetching data:", error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-white text-lg">جاري تحميل البيانات...</p>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <p className="text-white text-lg">لم يتم العثور على البيانات</p>
      </div>
    );
  }

  const profitColor = metrics.totalProfit >= 0 ? "text-green-500" : "text-red-500";
  const profitBgColor = metrics.totalProfit >= 0 ? "bg-green-500/10" : "bg-red-500/10";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4 md:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">لوحة تحكم استراتيجية السكالبينج</h1>
        <p className="text-slate-400">مراقبة أداء البوت التجاري في الوقت الفعلي</p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Total Profit Card */}
        <Card className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              إجمالي الأرباح
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${profitColor}`}>
              ${metrics.totalProfit.toFixed(2)}
            </div>
            <p className="text-xs text-slate-500 mt-1">من رأس المال الأولي</p>
          </CardContent>
        </Card>

        {/* Win Rate Card */}
        <Card className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Target className="w-4 h-4" />
              نسبة النجاح
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-400">{metrics.winRate.toFixed(2)}%</div>
            <p className="text-xs text-slate-500 mt-1">من إجمالي الصفقات</p>
          </CardContent>
        </Card>

        {/* Total Trades Card */}
        <Card className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Zap className="w-4 h-4" />
              عدد الصفقات
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-400">{metrics.totalTrades}</div>
            <p className="text-xs text-slate-500 mt-1">صفقة منفذة</p>
          </CardContent>
        </Card>

        {/* Final Balance Card */}
        <Card className={`border-slate-700 hover:border-slate-600 transition-colors ${profitBgColor}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-300 flex items-center gap-2">
              {metrics.finalBalance >= 1000 ? (
                <TrendingUp className="w-4 h-4 text-green-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
              الرصيد النهائي
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${profitColor}`}>
              ${metrics.finalBalance.toFixed(2)}
            </div>
            <p className="text-xs text-slate-500 mt-1">من أصل 1000 دولار</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Equity Curve */}
        <Card className="bg-slate-800 border-slate-700 col-span-1 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-white">منحنى رأس المال</CardTitle>
            <CardDescription>تطور الرصيد عبر الصفقات</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={equityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="trade" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #475569",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="#3b82f6"
                  dot={false}
                  strokeWidth={2}
                  name="الرصيد"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Win/Loss Distribution */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">توزيع الصفقات</CardTitle>
            <CardDescription>الصفقات الرابحة والخاسرة</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #475569",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Performance Metrics */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">مؤشرات الأداء</CardTitle>
            <CardDescription>ملخص الإحصائيات الرئيسية</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">متوسط الربح للصفقة</span>
              <span className="text-white font-semibold">
                ${(metrics.totalProfit / metrics.totalTrades).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">عدد الصفقات الرابحة</span>
              <span className="text-green-400 font-semibold">
                {metrics.trades.filter((t) => t.pnl > 0).length}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">عدد الصفقات الخاسرة</span>
              <span className="text-red-400 font-semibold">
                {metrics.trades.filter((t) => t.pnl <= 0).length}
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-slate-400">أكبر ربح</span>
              <span className="text-blue-400 font-semibold">
                ${Math.max(...metrics.trades.map((t) => t.pnl)).toFixed(2)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 justify-center">
        <Button className="bg-blue-600 hover:bg-blue-700 text-white">تحديث البيانات</Button>
        <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700">
          تحميل التقرير
        </Button>
      </div>
    </div>
  );
}
