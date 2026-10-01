using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;

namespace Reports;

public class ReportExporter
{
    public void Export(string path, IEnumerable<string> rows)
    {
        var stream = new FileStream(path, FileMode.Create);
        var writer = new StreamWriter(stream);
        foreach (var row in rows)
        {
            writer.WriteLine(row);
        }
        writer.Flush();
    }

    public async void ExportLater(string path, IEnumerable<string> rows)
    {
        await Task.Delay(1000);
        Export(path, rows);
    }
}
