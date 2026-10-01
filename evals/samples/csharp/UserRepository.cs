using System;
using Microsoft.Data.SqlClient;

namespace Accounts;

public class UserRepository
{
    private readonly string _connectionString;

    public UserRepository(string connectionString)
    {
        _connectionString = connectionString;
    }

    public bool IsAdmin(string userName)
    {
        try
        {
            using var connection = new SqlConnection(_connectionString);
            connection.Open();
            using var command = new SqlCommand(
                "SELECT IsAdmin FROM Users WHERE UserName = '" + userName + "'", connection);
            return (bool)command.ExecuteScalar();
        }
        catch (Exception)
        {
            return false;
        }
    }
}
